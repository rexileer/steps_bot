"""
Сервис для работы с реферальной системой
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.steps_bot.db.models.user import User
from app.steps_bot.db.models.family import Family
from app.steps_bot.db.models.referral import Referral
from app.steps_bot.db.repo import get_session
from app.steps_bot.services.ledger_service import accrue_steps_points
from app.steps_bot.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# Константы для настроек реферальной системы
REFERRAL_REWARD_PERCENT_KEY = "referral_reward_percent"
DEFAULT_REFERRAL_REWARD_PERCENT = 10  # 10% по умолчанию


async def get_referral_reward_percent() -> int:
    """Получить процент вознаграждения за реферала из настроек."""
    percent_str = await SettingsService.get_setting(REFERRAL_REWARD_PERCENT_KEY)
    if percent_str:
        try:
            return int(percent_str)
        except ValueError:
            logger.warning(f"Invalid referral reward percent: {percent_str}, using default")
    return DEFAULT_REFERRAL_REWARD_PERCENT


async def set_referral_reward_percent(percent: int) -> None:
    """Установить процент вознаграждения за реферала."""
    await SettingsService.set_setting(REFERRAL_REWARD_PERCENT_KEY, str(percent))


async def create_referral(
    session: AsyncSession,
    user_telegram_id: int,
    inviter_telegram_id: int,
) -> Optional[Referral]:
    """
    Создает реферальную связь между пользователем и пригласившим.
    ВАЖНО: Баллы пригласившему начисляются не сразу, а при каждом заработке реферала.
    
    Возвращает созданную запись Referral или None, если:
    - Пользователь уже имеет пригласившего
    - Пользователь пытается пригласить сам себя
    - Один из пользователей не найден
    """
    # Получаем обоих пользователей
    user = await session.scalar(
        select(User).where(User.telegram_id == user_telegram_id)
    )
    inviter = await session.scalar(
        select(User).where(User.telegram_id == inviter_telegram_id)
    )
    
    if not user or not inviter:
        logger.warning(f"User or inviter not found: user={user_telegram_id}, inviter={inviter_telegram_id}")
        return None
    
    # Проверка на самореферал
    if user.id == inviter.id:
        logger.warning(f"User {user_telegram_id} tried to refer themselves")
        return None
    
    # Проверка, что пользователь еще не был приглашен
    existing = await session.scalar(
        select(Referral).where(Referral.user_id == user.id)
    )
    if existing:
        logger.warning(f"User {user_telegram_id} already has a referrer")
        return None
    
    # Создаем реферальную связь (без начального вознаграждения)
    referral = Referral(
        user_id=user.id,
        inviter_id=inviter.id,
        reward_points=0,  # Будет накапливаться при заработке реферала
    )
    session.add(referral)
    await session.flush()
    await session.commit()
    
    logger.info(f"Referral created: user={user.telegram_id}, inviter={inviter.telegram_id}")
    return referral


async def reward_inviter_for_referral_earning(
    session: AsyncSession,
    user_id: int,
    earned_amount: int,
) -> Optional[int]:
    """
    Начисляет пригласившему процент от заработка реферала.
    
    Args:
        session: Сессия БД
        user_id: ID пользователя (реферала), который заработал баллы
        earned_amount: Количество заработанных баллов
    
    Returns:
        Optional[int]: Количество начисленных баллов пригласившему или None
    """
    # Проверяем, является ли пользователь чьим-то рефералом
    referral = await session.scalar(
        select(Referral).where(Referral.user_id == user_id)
    )
    
    if not referral:
        return None  # Пользователь не является рефералом
    
    # Получаем процент вознаграждения
    reward_percent = await get_referral_reward_percent()
    
    # Рассчитываем вознаграждение (округляем вниз)
    reward_amount = int((earned_amount * reward_percent) / 100)
    
    if reward_amount <= 0:
        return None
    
    # Обновляем накопленное вознаграждение в записи реферала
    referral.reward_points += reward_amount
    
    # Получаем реферала для информации
    referred_user = await session.scalar(
        select(User).where(User.id == user_id)
    )
    
    # Начисляем баллы пригласившему напрямую (без создания пользовательских записей для статистики)
    from app.steps_bot.db.models.ledger import LedgerEntry, OwnerType, OperationType
    from app.steps_bot.db.models.family import Family
    import datetime as dt
    
    inviter = await session.scalar(
        select(User).where(User.id == referral.inviter_id).with_for_update()
    )
    
    if inviter.family_id:
        # Начисляем в семейный баланс
        fam = await session.scalar(
            select(Family).where(Family.id == inviter.family_id).with_for_update()
        )
        if fam:
            fam.balance = int(fam.balance) + reward_amount
            entry = LedgerEntry(
                owner_type=OwnerType.FAMILY,
                family_id=fam.id,
                operation=OperationType.PROMO_ACCRUAL,  # Используем PROMO_ACCRUAL для реферальных
                amount=reward_amount,
                balance_after=int(fam.balance),
                title="Реферальное начисление",
                description=f"Вознаграждение {reward_percent}% от заработка реферала @{referred_user.username or referred_user.telegram_id}",
                created_at=dt.datetime.now(tz=dt.timezone.utc),
            )
            session.add(entry)
    else:
        # Начисляем на личный баланс
        inviter.balance = int(inviter.balance) + reward_amount
        entry = LedgerEntry(
            owner_type=OwnerType.USER,
            user_id=inviter.id,
            operation=OperationType.PROMO_ACCRUAL,  # Используем PROMO_ACCRUAL для реферальных
            amount=reward_amount,
            balance_after=int(inviter.balance),
            title="Реферальное начисление",
            description=f"Вознаграждение {reward_percent}% от заработка реферала @{referred_user.username or referred_user.telegram_id}",
            created_at=dt.datetime.now(tz=dt.timezone.utc),
        )
        session.add(entry)
    
    await session.flush()
    logger.info(
        f"Referral reward: inviter_id={referral.inviter_id}, "
        f"referral_id={user_id}, earned={earned_amount}, "
        f"reward={reward_amount} ({reward_percent}%)"
    )
    
    return reward_amount


async def get_referral_stats(telegram_id: int) -> Tuple[int, int]:
    """
    Возвращает статистику по рефералам для пользователя.
    
    Returns:
        Tuple[int, int]: (количество рефералов, заработанные баллы)
    """
    async with get_session() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        if not user:
            return 0, 0
        
        # Подсчитываем количество рефералов
        referral_count = await session.scalar(
            select(func.count(Referral.id)).where(Referral.inviter_id == user.id)
        )
        
        # Подсчитываем заработанные баллы
        earned_points = await session.scalar(
            select(func.sum(Referral.reward_points)).where(Referral.inviter_id == user.id)
        )
        
        return int(referral_count or 0), int(earned_points or 0)


async def get_referrals_list(telegram_id: int, offset: int = 0, limit: int = 10) -> List[str]:
    """
    Возвращает список рефералов пользователя.
    
    Returns:
        List[str]: Список имен рефералов
    """
    async with get_session() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        if not user:
            return []
        
        # Получаем список рефералов с информацией о пользователях
        result = await session.execute(
            select(Referral, User)
            .join(User, Referral.user_id == User.id)
            .where(Referral.inviter_id == user.id)
            .order_by(Referral.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        referrals = []
        for referral, referred_user in result:
            # Формируем имя реферала
            if referred_user.first_name:
                name = f"{referred_user.first_name}"
                if referred_user.last_name:
                    name += f" {referred_user.last_name}"
            else:
                name = f"@{referred_user.username}" if referred_user.username else f"ID: {referred_user.telegram_id}"
            
            referrals.append(name)
        
        return referrals


async def generate_referral_link(telegram_id: int, bot_username: str) -> str:
    """
    Генерирует реферальную ссылку для пользователя.
    
    Args:
        telegram_id: Telegram ID пользователя
        bot_username: Username бота (без @)
    
    Returns:
        str: Реферальная ссылка вида t.me/bot?start=ref_123456
    """
    return f"https://t.me/{bot_username}?start=ref_{telegram_id}"


def parse_referral_code(start_param: Optional[str]) -> Optional[int]:
    """
    Парсит start параметр и извлекает telegram_id пригласившего.
    
    Args:
        start_param: Параметр из /start команды (например, "ref_123456")
    
    Returns:
        Optional[int]: Telegram ID пригласившего или None
    """
    if not start_param or not start_param.startswith("ref_"):
        return None
    
    try:
        inviter_id = int(start_param[4:])  # Убираем префикс "ref_"
        return inviter_id
    except ValueError:
        logger.warning(f"Invalid referral code: {start_param}")
        return None

