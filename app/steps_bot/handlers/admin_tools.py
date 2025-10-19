from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message


router = Router()


@router.message(F.text.startswith('/order_check'))
async def order_check(msg: Message) -> None:
    """Скрытая команда: /order_check <UUID> — DEPRECATED (CDEK удален)."""
    await msg.answer('Команда больше не поддерживается. CDEK интеграция удалена. Используйте GET /order API вместо этого.')


@router.message(F.text.startswith('/orders_list'))
async def orders_list(msg: Message) -> None:
    """Скрытая команда: /orders_list [page] [size] — DEPRECATED (CDEK удален)."""
    await msg.answer('Команда больше не поддерживается. CDEK интеграция удалена. Используйте GET /order API вместо этого.')


@router.message(F.text.startswith('/order_delete'))
async def order_delete(msg: Message) -> None:
    """Скрытая команда: /order_delete <UUID> — DEPRECATED (CDEK удален)."""
    await msg.answer('Команда больше не поддерживается. CDEK интеграция удалена.')


