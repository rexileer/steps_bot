from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple
from datetime import date as date_type
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
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
from app.steps_bot.db.models.pvz import PVZ


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
    pvz_id: str,
    recipient_first_name: str = "",
    recipient_last_name: str = "",
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
        pvz_id=pvz_id,
        recipient_first_name=recipient_first_name,
        recipient_last_name=recipient_last_name,
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


async def replace_pvz_list(session: AsyncSession, pvz_list: List[Dict[str, str]]) -> int:
    """
    Удаляет все ПВЗ из БД и вставляет новый список.
    
    Args:
        session: async сессия БД
        pvz_list: список словарей {"id": "...", "full_address": "..."}
    
    Returns:
        количество сохраненных ПВЗ
    """
    # Удаляем все старые ПВЗ
    await session.execute(delete(PVZ))
    
    # Вставляем новые
    pvz_objects = [
        PVZ(id=item["id"], full_address=item["full_address"])
        for item in pvz_list
    ]
    session.add_all(pvz_objects)
    await session.flush()
    
    return len(pvz_objects)


async def get_pvz_by_city(session: AsyncSession, city: str) -> List[PVZ]:
    """
    Возвращает список ПВЗ, где full_address содержит город.
    
    Args:
        session: async сессия БД
        city: название города для фильтрации
    
    Returns:
        список объектов PVZ
    """
    query = select(PVZ).where(PVZ.full_address.ilike(f"%{city}%")).order_by(PVZ.full_address)
    result = await session.execute(query)
    return result.scalars().all()


def _parse_full_name(full_name: str) -> tuple[str, str]:
    """
    Парсит полное имя в формате: Фамилия Имя Отчество
    Возвращает: (first_name=Имя, last_name=Фамилия)
    Отчество игнорируется.
    """
    if not full_name:
        return "", ""
    
    parts = full_name.strip().split()
    
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        # Только фамилия
        return "", parts[0]
    elif len(parts) >= 2:
        # Фамилия, Имя, (Отчество)
        last_name = parts[0]
        first_name = parts[1]
        return first_name, last_name
    
    return "", ""


async def get_orders_between(
    session: AsyncSession,
    date_from: date_type,
    date_to: date_type,
) -> List[Dict[str, Any]]:
    """
    Возвращает список заказов за диапазон дат с необходимыми полями.
    """
    query = (
        select(
            Order.recipient_first_name,
            Order.recipient_last_name,
            User.phone,
            User.email,
            Order.id,
            Order.pvz_id,
            Order.created_at,
            Product.product_code
        )
        .join(Order, Order.user_id == User.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Order.created_at >= date_from)
        .where(Order.created_at <= date_to)
        .order_by(Order.created_at.desc())
    )
    
    result = await session.execute(query)
    rows = result.all()
    
    # MSK timezone (UTC+3)
    msk_tz = timezone(timedelta(hours=3))
    
    orders = []
    for row in rows:
        first_name, last_name, phone, email, order_id, pvz_id, created_at, product_code = row
        
        # Форматируем время в MSK без микросекунд
        if created_at:
            # Конвертируем UTC в MSK
            msk_time = created_at.astimezone(msk_tz)
            # Форматируем без микросекунд и часового пояса
            created_at_str = msk_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            created_at_str = ""
        
        orders.append({
            "first_name": first_name or "",
            "last_name": last_name or "",
            "phone": phone or "",
            "email": email or "",
            "pvz_id": pvz_id or "",
            "order_id": str(order_id),
            "created_at": created_at_str,
            "product_code": str(product_code) if product_code else "",
        })
    
    return orders
