from typing import Optional, Sequence, Tuple

from sqlalchemy import select

from app.steps_bot.db.repo import get_session, get_user_with_family, family_points_enough, deduct_family_points_proportional
from app.steps_bot.db.models.promo import PromoGroup, PromoCode


async def list_active_groups() -> Sequence[PromoGroup]:
    """
    Возвращает активные группы промокодов.
    """
    async with get_session() as session:
        res = await session.execute(
            select(PromoGroup)
            .where(PromoGroup.is_active.is_(True))
            .order_by(PromoGroup.discount_percent.desc(), PromoGroup.name.asc())
        )
        return res.scalars().all()


async def purchase_and_acquire_code_family(group_id: int, user_id_or_telegram: int) -> Tuple[Optional[str], Optional[PromoGroup], Optional[str]]:
    """
    Покупает промокод за баллы семьи и выдаёт код из группы.
    Возвращает (код|None, группа|None, ошибка|None).
    """
    async with get_session() as session:
        async with session.begin():
            group = await session.get(PromoGroup, group_id)
            if not group or not group.is_active:
                return None, group, "Группа недоступна"

            res = await session.execute(
                select(PromoCode)
                .where(
                    PromoCode.group_id == group_id,
                    PromoCode.is_active.is_(True),
                    PromoCode.used_count < PromoCode.max_uses,
                )
                .order_by(PromoCode.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            code_obj = res.scalars().first()
            if not code_obj:
                return None, group, "В данной группе нет промокодов"

            user, family, _ = await get_user_with_family(session, user_id_or_telegram)
            if not family:
                return None, group, "Для покупки требуется семья"

            price = int(group.price_points or 0)
            enough = await family_points_enough(session, family.id, price)
            if not enough:
                return None, group, f"Недостаточно баллов семьи: нужно {price}"

            await deduct_family_points_proportional(session, family.id, price)

            code_obj.used_count += 1
            if code_obj.used_count >= code_obj.max_uses:
                code_obj.is_active = False

            await session.flush()
            return code_obj.code, group, None
        

async def acquire_code(group_id: int) -> Tuple[Optional[str], Optional[PromoGroup]]:
    """
    Атомарно выдаёт код из группы и помечает использование.
    """
    async with get_session() as session:
        async with session.begin():
            group = await session.get(PromoGroup, group_id)
            if not group or not group.is_active:
                return None, group

            res = await session.execute(
                select(PromoCode)
                .where(
                    PromoCode.group_id == group_id,
                    PromoCode.is_active.is_(True),
                    PromoCode.used_count < PromoCode.max_uses,
                )
                .order_by(PromoCode.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            code_obj = res.scalars().first()
            if not code_obj:
                return None, group

            code_obj.used_count += 1
            if code_obj.used_count >= code_obj.max_uses:
                code_obj.is_active = False

            await session.flush()
            return code_obj.code, group
