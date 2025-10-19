from __future__ import annotations

import json
import time
from html import escape
from typing import Any, Dict, Tuple, Optional

import contextlib
from app.steps_bot.settings import config
from app.steps_bot.states.order import OrderInput
from app.steps_bot.db import repo
from app.steps_bot.services.ledger_service import (
    purchase_from_family_proportional,
    purchase_from_user,
)


def _order_number(user_id: int, product_id: int) -> str:
    """
    Возвращает номер заказа.
    """
    ts = int(time.time())
    return f"TG-{user_id}-{product_id}-{ts}"


async def load_product_summary(product_id: int) -> Optional[Dict[str, Any]]:
    """
    Возвращает краткую информацию о товаре для подтверждения.
    """
    async with repo.get_session() as session:
        result = await repo.get_product_with_category(session, product_id)
        if not result:
            return None
        product, category = result
        return {
            "product_id": product.id,
            "title": product.title,
            "category": category.name if category else None,
            "price": product.price,
        }


async def finalize_successful_order(
    user_id: int,
    product_id: int,
    pvz_id: str,
    full_name: str = "",
) -> Dict[str, Any]:
    """
    Создаёт заказ, списывает баллы с семьи пропорционально и пишет проводки.
    
    Args:
        user_id: ID пользователя (telegram или БД)
        product_id: ID товара
        pvz_id: ID ПВЗ для доставки
        full_name: полное имя получателя (для сохранения в профиль)
    """
    async with repo.get_session() as session:
        result = await repo.get_product_with_category(session, product_id)
        if not result:
            raise ValueError("Товар недоступен")

        product, category = result
        user, family, _ = await repo.get_user_with_family(session, user_id)
        
        # Парсим ФИО для сохранения в заказ
        first_name, last_name = "", ""
        if full_name:
            parts = full_name.strip().split()
            if len(parts) >= 2:
                last_name = parts[0]  # Фамилия
                first_name = parts[1]  # Имя
            elif len(parts) == 1:
                last_name = parts[0]  # Только фамилия
        
        # Проверяем доступность по семье или по личному балансу
        if family:
            enough_family = await repo.family_points_enough(session, family.id, int(product.price))
            if not enough_family:
                raise ValueError("Недостаточно баллов семьи")
        else:
            # Проверяем личный баланс
            if int(user.balance) < int(product.price):
                raise ValueError("Недостаточно баллов")

        order = await repo.create_order_with_item(
            session=session,
            user_id=user.id,
            product=product,
            pvz_id=pvz_id,
            recipient_first_name=first_name,
            recipient_last_name=last_name,
        )

        if family:
            await purchase_from_family_proportional(
                session=session,
                family_id=family.id,
                amount=int(product.price),
                order_id=order.id,
                title="Покупка в каталоге",
                description=product.title,
            )
        else:
            await purchase_from_user(
                session=session,
                user_id_or_telegram=user.id,
                amount=int(product.price),
                order_id=order.id,
                title="Покупка в каталоге",
                description=product.title,
            )

        await repo.delete_product(session, product.id)

        return {
            "order_id": order.id,
            "product_title": product.title,
            "category_name": category.name if category else None,
            "price": int(product.price),
            "pvz_id": pvz_id,
        }


def format_order_message(info: Dict[str, Any], delivery_kind: str, destination: str) -> str:
    """
    Возвращает финальное сообщение пользователю (точное, как в ТЗ).
    """
    return "Спасибо за участие в игре! \n🎁 Как идет Ваш подарок можно увидеть по ссылке, которую Яндекс выслал в смс."


async def probe_cdek_order(order: OrderInput, user_id: int, city_code: int | None) -> tuple[bool, str]:
    """
    Заглушка функции (больше не используется, так как CDEK убран).
    """
    return False, "CDEK integration removed"


async def ensure_purchase_allowed(user_id: int, product_id: int) -> tuple[bool, str]:
    """
    Проверяет доступность покупки: товар активен, у пользователя есть семья,
    и суммарных баллов семьи достаточно для цены товара.
    Возвращает (ok, сообщение_для_пользователя).
    """
    async with repo.get_session() as session:
        result = await repo.get_product_with_category(session, product_id)
        if not result:
            return False, "Товар недоступен или уже куплен."

        product, _ = result
        try:
            user, family, _ = await repo.get_user_with_family(session, user_id)
        except ValueError:
            return False, "Пользователь не найден."

        if family:
            enough_family = await repo.family_points_enough(session, family.id, int(product.price))
            if not enough_family:
                return False, "Недостаточно баллов семьи."
            return True, "ok"

        # Без семьи — достаточно ли личных баллов
        if int(user.balance) < int(product.price):
            return False, "Недостаточно баллов."

        return True, "ok"
