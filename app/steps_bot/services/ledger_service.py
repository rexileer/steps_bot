from __future__ import annotations

import datetime as dt
from typing import Optional, Sequence, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.steps_bot.db.models.family import Family
from app.steps_bot.db.models.user import User
from app.steps_bot.db.models.ledger import (
    LedgerEntry,
    OwnerType,
    OperationType,
)


async def transfer_user_to_family(
    session: AsyncSession,
    user_id_or_telegram: int,
    family_id: int,
    title: str = "Перевод в семейный баланс",
    description: Optional[str] = None,
) -> Optional[LedgerEntry]:
    """
    Переносит весь личный баланс пользователя в баланс семьи. Возвращает запись журнала перевода
    (owner_type=family), если было что переносить. Если баланс нулевой — возвращает None.
    """
    user = await _get_user_by_id_or_telegram(session, user_id_or_telegram)
    if not user:
        raise ValueError("Пользователь не найден")

    fam = (
        await session.execute(select(Family).where(Family.id == family_id).with_for_update())
    ).scalar_one_or_none()
    if not fam:
        raise ValueError("Семья не найдена")

    q = select(User).where(User.id == (user.id)).with_for_update()
    ul = (await session.execute(q)).scalar_one()
    amount = int(ul.balance)
    if amount <= 0:
        return None

    ul.balance = 0
    fam.balance = int(fam.balance) + amount

    entry = LedgerEntry(
        owner_type=OwnerType.FAMILY,
        family_id=fam.id,
        operation=OperationType.TRANSFER,
        amount=amount,
        balance_after=int(fam.balance),
        title=title,
        description=description,
        created_at=dt.datetime.now(tz=dt.timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def _get_user_by_id_or_telegram(
    session: AsyncSession,
    user_id_or_telegram: int,
) -> Optional[User]:
    """
    Возвращает пользователя по users.id или users.telegram_id.
    """
    user = (
        await session.execute(
            select(User).where(User.id == user_id_or_telegram).limit(1)
        )
    ).scalar_one_or_none()
    if user:
        return user
    user = (
        await session.execute(
            select(User).where(User.telegram_id == user_id_or_telegram).limit(1)
        )
    ).scalar_one_or_none()
    return user


async def accrue_steps_points(
    session: AsyncSession,
    user_id_or_telegram: int,
    amount: int,
    title: str = "Начисление за шаги",
    description: Optional[str] = None,
) -> LedgerEntry:
    """
    Начисляет баллы за шаги: если пользователь состоит в семье — на баланс семьи,
    иначе — на личный баланс. Пишет запись в журнал.
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    user = await _get_user_by_id_or_telegram(session, user_id_or_telegram)
    if not user:
        raise ValueError("Пользователь не найден")

    if user.family_id:
        fam = (
            await session.execute(
                select(Family).where(Family.id == user.family_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not fam:
            raise ValueError("Семья не найдена")
        fam.balance = int(fam.balance) + int(amount)
        entry = LedgerEntry(
            owner_type=OwnerType.FAMILY,
            family_id=fam.id,
            operation=OperationType.STEPS_ACCRUAL,
            amount=int(amount),
            balance_after=int(fam.balance),
            title=title,
            description=description,
            created_at=dt.datetime.now(tz=dt.timezone.utc),
        )
    else:
        q = select(User).where(User.id == user.id).with_for_update()
        user_locked = (await session.execute(q)).scalar_one()
        user_locked.balance = int(user_locked.balance) + int(amount)
        entry = LedgerEntry(
            owner_type=OwnerType.USER,
            user_id=user_locked.id,
            operation=OperationType.STEPS_ACCRUAL,
            amount=int(amount),
            balance_after=int(user_locked.balance),
            title=title,
            description=description,
            created_at=dt.datetime.now(tz=dt.timezone.utc),
        )
    session.add(entry)
    await session.flush()
    return entry


async def purchase_from_family_proportional(
    session: AsyncSession,
    family_id: int,
    amount: int,
    order_id: Optional[int] = None,
    title: str = "Покупка",
    description: Optional[str] = None,
) -> Sequence[LedgerEntry]:
    """
    Списывает баллы за покупку с семьи: сначала с Family.balance, затем пропорционально с балансов членов семьи.
    Создаёт отдельную запись в журнале на каждого владельца, у кого списаны баллы.
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    family = (
        await session.execute(
            select(Family).where(Family.id == family_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not family:
        raise ValueError("Семья не найдена")

    members = (
        await session.execute(
            select(User).where(User.family_id == family_id).with_for_update()
        )
    ).scalars().all()

    total_available = int(family.balance) + sum(int(u.balance) for u in members)
    if total_available < int(amount):
        raise ValueError("Недостаточно баллов семьи")

    remaining = int(amount)
    entries: list[LedgerEntry] = []

    take_family = min(remaining, int(family.balance))
    if take_family > 0:
        family.balance = int(family.balance) - take_family
        entries.append(
            LedgerEntry(
                owner_type=OwnerType.FAMILY,
                family_id=family.id,
                operation=OperationType.PURCHASE,
                amount=-take_family,
                balance_after=int(family.balance),
                order_id=order_id,
                title=title,
                description=description,
                created_at=dt.datetime.now(tz=dt.timezone.utc),
            )
        )
        remaining -= take_family

    if remaining == 0 or not members:
        for e in entries:
            session.add(e)
        await session.flush()
        return entries

    members_total = sum(int(u.balance) for u in members)
    if members_total == 0:
        for e in entries:
            session.add(e)
        await session.flush()
        return entries

    allocated = 0
    for i, u in enumerate(members):
        if i < len(members) - 1:
            part = (int(u.balance) * remaining) // members_total
            part = min(part, int(u.balance))
        else:
            part = min(remaining - allocated, int(u.balance))
        if part <= 0:
            continue
        u.balance = int(u.balance) - part
        allocated += part
        entries.append(
            LedgerEntry(
                owner_type=OwnerType.USER,
                user_id=u.id,
                operation=OperationType.PURCHASE,
                amount=-part,
                balance_after=int(u.balance),
                order_id=order_id,
                title=title,
                description=description,
                created_at=dt.datetime.now(tz=dt.timezone.utc),
            )
        )

    for e in entries:
        session.add(e)
    await session.flush()
    return entries


async def purchase_from_user(
    session: AsyncSession,
    user_id_or_telegram: int,
    amount: int,
    order_id: Optional[int] = None,
    title: str = "Покупка",
    description: Optional[str] = None,
) -> LedgerEntry:
    """
    Списывает баллы за покупку с личного счёта пользователя и пишет запись в журнал.
    """
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    user = await _get_user_by_id_or_telegram(session, user_id_or_telegram)
    if not user:
        raise ValueError("Пользователь не найден")

    q = select(User).where(User.id == user.id).with_for_update()
    user_locked = (await session.execute(q)).scalar_one()
    if int(user_locked.balance) < int(amount):
        raise ValueError("Недостаточно баллов")

    user_locked.balance = int(user_locked.balance) - int(amount)

    entry = LedgerEntry(
        owner_type=OwnerType.USER,
        user_id=user_locked.id,
        operation=OperationType.PURCHASE,
        amount=-int(amount),
        balance_after=int(user_locked.balance),
        order_id=order_id,
        title=title,
        description=description,
        created_at=dt.datetime.now(tz=dt.timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_history_for_user_with_family(
    session: AsyncSession,
    user_id_or_telegram: int,
    limit: int = 20,
) -> Tuple[User, Optional[Family], Sequence[LedgerEntry]]:
    """
    Возвращает пользователя, его семью и последние операции по пользователю и семье.
    """
    user = await _get_user_by_id_or_telegram(session, user_id_or_telegram)
    if not user:
        raise ValueError("Пользователь не найден")

    family = None
    if user.family_id:
        family = (
            await session.execute(
                select(Family).where(Family.id == user.family_id).limit(1)
            )
        ).scalar_one_or_none()

    if family:
        rows = (
            await session.execute(
                select(LedgerEntry)
                .where(
                    (
                        (LedgerEntry.owner_type == OwnerType.USER)
                        & (LedgerEntry.user_id == user.id)
                    )
                    | (
                        (LedgerEntry.owner_type == OwnerType.FAMILY)
                        & (LedgerEntry.family_id == family.id)
                    )
                )
                .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return user, family, rows

    rows = (
        await session.execute(
            select(LedgerEntry)
            .where(
                (LedgerEntry.owner_type == OwnerType.USER)
                & (LedgerEntry.user_id == user.id)
            )
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    return user, None, rows
