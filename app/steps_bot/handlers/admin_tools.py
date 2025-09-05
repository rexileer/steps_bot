from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from app.steps_bot.services.cdek_client import cdek_client


router = Router()


@router.message(F.text.startswith('/order_check'))
async def order_check(msg: Message) -> None:
    """Скрытая команда: /order_check <UUID> — получить сведения по заказу CDEK."""
    parts = (msg.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer('Формат: /order_check <UUID>')
        return
    uuid = parts[1].strip()
    try:
        data = await cdek_client.get_order_by_uuid(uuid)
    except Exception as e:
        await msg.answer(f'Ошибка: {e}')
        return
    if not data.get('ok'):
        await msg.answer(f"API: {data.get('status')} {data.get('text')}")
        return
    await msg.answer(str(data.get('data') or {}))


@router.message(F.text.startswith('/orders_list'))
async def orders_list(msg: Message) -> None:
    """Скрытая команда: /orders_list [page] [size] — список заказов по API аккаунта."""
    parts = (msg.text or '').split()
    page = 0
    size = 10
    if len(parts) >= 2:
        try:
            page = int(parts[1])
        except Exception:
            pass
    if len(parts) >= 3:
        try:
            size = int(parts[2])
        except Exception:
            pass
    try:
        data = await cdek_client.list_orders(page=page, size=size)
    except Exception as e:
        await msg.answer(f'Ошибка: {e}')
        return
    if not data.get('ok'):
        await msg.answer(f"API: {data.get('status')} {data.get('text')}")
        return
    await msg.answer(str(data.get('data') or {}))


@router.message(F.text.startswith('/order_delete'))
async def order_delete(msg: Message) -> None:
    """Скрытая команда: /order_delete <UUID> — удалить заказ CDEK (в статусе 'Создан')."""
    parts = (msg.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer('Формат: /order_delete <UUID>')
        return
    uuid = parts[1].strip()
    try:
        data = await cdek_client.delete_order(uuid)
    except Exception as e:
        await msg.answer(f'Ошибка: {e}')
        return
    if not data.get('ok'):
        await msg.answer(f"API: {data.get('status')} {data.get('text')}")
        return
    await msg.answer('Удаление принято (если заказ в статусе "Создан").')


