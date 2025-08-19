from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.steps_bot.db.session import AsyncSessionLocal
from app.steps_bot.db.models.catalog import (
    CatalogCategory,
    Order,
    OrderItem,
    Product,
)
from app.steps_bot.db.models.user import User
from app.steps_bot.db.models.family import Family
from app.steps_bot.db.models.catalog import Order, OrderItem


@asynccontextmanager
async def get_session():
    """
    Возвращает асинхронную сессию БД с автокоммитом/ролбэком.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_product_with_category(
    session: AsyncSession,
    product_id: int,
) -> Optional[Tuple[Product, Optional[CatalogCategory]]]:
    """
    Возвращает товар и его категорию, если товар активен.
    """
    q = (
        select(Product, CatalogCategory)
        .join(CatalogCategory, CatalogCategory.id == Product.category_id, isouter=True)
        .where(Product.id == product_id, Product.is_active.is_(True))
        .limit(1)
    )
    row = (await session.execute(q)).first()
    if not row:
        return None
    product, category = row
    return product, category


async def _resolve_user(session: AsyncSession, user_id_or_telegram: int) -> Optional[User]:
    """
    Возвращает пользователя по users.id или по users.telegram_id.
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


async def get_user_with_family(
    session: AsyncSession,
    user_id: int,
) -> Tuple[User, Optional[Family], List[object]]:
    """
    Возвращает пользователя и его семью по users.id или users.telegram_id.
    """
    user = await _resolve_user(session, user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    family = None
    if user.family_id:
        family = (
            await session.execute(
                select(Family).where(Family.id == user.family_id).limit(1)
            )
        ).scalar_one_or_none()
    return user, family, []


async def family_points_enough(
    session: AsyncSession,
    family_id: int,
    amount: int,
) -> bool:
    """
    Проверяет достаточность суммарных баллов семьи: баланс семьи + сумма баллов участников.
    """
    family = (
        await session.execute(select(Family).where(Family.id == family_id).limit(1))
    ).scalar_one_or_none()
    if not family:
        return False

    members = (
        await session.execute(select(User).where(User.family_id == family_id))
    ).scalars().all()

    total = int(family.balance) + sum(int(u.balance) for u in members)
    return total >= int(amount)


async def deduct_family_points_proportional(
    session: AsyncSession,
    family_id: int,
    amount: int,
) -> None:
    """
    Списывает баллы сначала с баланса семьи, затем пропорционально с балансов участников.
    """
    family = (
        await session.execute(select(Family).where(Family.id == family_id).limit(1))
    ).scalar_one_or_none()
    if not family:
        raise ValueError("Семья не найдена")

    members = (
        await session.execute(select(User).where(User.family_id == family_id))
    ).scalars().all()

    total_available = int(family.balance) + sum(int(u.balance) for u in members)
    if total_available < int(amount):
        raise ValueError("Недостаточно баллов семьи")

    remaining = int(amount)

    take_from_family = min(remaining, int(family.balance))
    family.balance = int(family.balance) - take_from_family
    remaining -= take_from_family

    if remaining == 0 or not members:
        return

    members_total = sum(int(u.balance) for u in members)
    if members_total == 0:
        return

    allocated_sum = 0
    for i, u in enumerate(members):
        if i < len(members) - 1:
            part = (int(u.balance) * remaining) // members_total
            part = min(part, int(u.balance))
            u.balance = int(u.balance) - part
            allocated_sum += part
        else:
            tail = min(remaining - allocated_sum, int(u.balance))
            u.balance = int(u.balance) - tail


async def create_order_with_item(
    session: AsyncSession,
    user_id: int,
    product,
    cdek_uuid: str,
) -> Order:
    """
    Создаёт заказ для реального users.id, найденного по id или telegram_id.
    """
    user = await _resolve_user(session, user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    order = Order(
        user_id=user.id,
        total_price=int(product.price),
        cdek_uuid=cdek_uuid,
    )
    session.add(order)
    await session.flush()
    item = OrderItem(order_id=order.id, product_id=product.id, qty=1)
    session.add(item)
    await session.flush()
    return order


async def delete_product(session: AsyncSession, product_id: int) -> None:
    """
    Деактивирует товар после покупки.
    """
    product = (
        await session.execute(select(Product).where(Product.id == product_id).limit(1))
    ).scalar_one_or_none()
    if not product:
        return
    product.is_active = False
    await session.flush()
