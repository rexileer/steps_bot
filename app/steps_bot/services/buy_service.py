from __future__ import annotations

import json
import time
from html import escape
from typing import Any, Dict, Tuple, Optional

from app.steps_bot.services.cdek_client import cdek_client
from app.steps_bot.settings import config
from app.steps_bot.states.order import OrderInput
from app.steps_bot.db import repo
from app.steps_bot.services.ledger_service import purchase_from_family_proportional


def _order_number(user_id: int, product_id: int) -> str:
    """
    Возвращает номер заказа для СДЭК.
    """
    ts = int(time.time())
    return f"TG-{user_id}-{product_id}-{ts}"


def _package_block(product_id: int, item_name: str) -> Dict[str, Any]:
    """
    Возвращает пакет с габаритами, весом и номенклатурой.
    """
    weight = config.DEFAULT_PACKAGE_WEIGHT_G
    return {
        "number": "1",
        "weight": weight,
        "length": config.DEFAULT_PACKAGE_L,
        "width": config.DEFAULT_PACKAGE_W,
        "height": config.DEFAULT_PACKAGE_H,
        "items": [
            {
                "name": item_name,
                "ware_key": str(product_id),
                "payment": {"value": 0},
                "cost": 0,
                "weight": weight,
                "amount": 1,
            }
        ],
    }


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


async def build_cdek_payload(order: OrderInput, user_id: int, city_code: int | None) -> Dict[str, Any]:
    """
    Строит JSON заказа СДЭК с учётом типа доставки.
    """
    to_city_code = city_code or await cdek_client.find_city_code(order.city)

    summary = await load_product_summary(order.product_id)
    item_name = (summary or {}).get("title") or f"Товар #{order.product_id}"

    base: Dict[str, Any] = {
        "type": 1,
        "number": _order_number(user_id=user_id, product_id=order.product_id),
        "tariff_code": config.CDEK_TARIFF_PVZ if order.delivery_type == "pvz" else config.CDEK_TARIFF_COURIER,
        "from_location": {"code": config.CDEK_FROM_CITY_CODE},
        "recipient": {
            "name": order.full_name,
            "phones": [{"number": order.phone}],
        },
        "packages": [_package_block(order.product_id, item_name)],
    }
    if order.delivery_type == "pvz":
        if not order.pvz_code:
            raise ValueError("Не указан код ПВЗ для доставки в ПВЗ")
        base["delivery_point"] = order.pvz_code
    else:
        addr = (order.address or "").strip()
        if not addr:
            raise ValueError("Не указан адрес для курьерской доставки")
        base["to_location"] = {"code": to_city_code, "address": addr}
    return base


async def submit_order_to_cdek(order: OrderInput, user_id: int, city_code: int | None) -> Tuple[bool, str]:
    """
    Отправляет заказ в СДЭК и возвращает результат.
    """
    payload = await build_cdek_payload(order, user_id=user_id, city_code=city_code)
    try:
        print("[CDEK] Payload:", json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass
    resp = await cdek_client.create_order(payload)
    if not resp.get("ok"):
        return False, f"Ошибка {resp.get('status')}: {resp.get('text')}"
    data = resp.get("data") or {}
    entity = data.get("entity") or {}
    uuid = entity.get("uuid") or ""
    if uuid:
        return True, uuid
    errors = data.get("errors") or []
    if errors:
        first = errors[0]
        code = first.get("code", "")
        msg = first.get("message", "")
        return False, f"{code} {msg}".strip()
    return False, "Не удалось создать заказ"


async def finalize_successful_order(
    user_id: int,
    product_id: int,
    cdek_uuid: str,
) -> Dict[str, Any]:
    """
    Создаёт заказ, списывает баллы с семьи пропорционально и пишет проводки.
    """
    async with repo.get_session() as session:
        result = await repo.get_product_with_category(session, product_id)
        if not result:
            raise ValueError("Товар недоступен")

        product, category = result
        user, family, _ = await repo.get_user_with_family(session, user_id)
        if not family:
            raise ValueError("Для оформления покупки требуется семья")

        enough = await repo.family_points_enough(session, family.id, int(product.price))
        if not enough:
            raise ValueError("Недостаточно баллов семьи")

        order = await repo.create_order_with_item(
            session=session,
            user_id=user.id,
            product=product,
            cdek_uuid=cdek_uuid,
        )

        await purchase_from_family_proportional(
            session=session,
            family_id=family.id,
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
            "cdek_uuid": cdek_uuid,
        }



def format_order_message(info: Dict[str, Any], delivery_kind: str, destination: str) -> str:
    """
    Возвращает текст подтверждения оформления заказа.
    """
    head = "✅ Заказ оформлен"
    lines = [
        head,
        "",
        f"Заказ № {escape(str(info['order_id']))}",
        f"Товар: {escape(str(info['product_title']))}",
    ]
    if info.get("category_name"):
        lines.append(f"Категория: {escape(str(info['category_name']))}")
    lines.extend(
        [
            f"Стоимость: {escape(str(info['price']))} баллов",
            f"Доставка: {'ПВЗ СДЭК' if delivery_kind == 'pvz' else 'Курьер СДЭК'}",
            f"Куда: {escape(destination or '')}",
            f"CDEK UUID: {escape(str(info['cdek_uuid']))}",
        ]
    )
    return "\n".join(lines)


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

        if not family:
            return False, "Для оформления покупки требуется семья."

        enough = await repo.family_points_enough(session, family.id, int(product.price))
        if not enough:
            return False, "Недостаточно баллов семьи."

        return True, "ok"
