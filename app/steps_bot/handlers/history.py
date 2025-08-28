from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.ledger import OwnerType
from app.steps_bot.presentation.keyboards.simple_kb import back_kb
from app.steps_bot.services.ledger_service import get_history_for_user_with_family

router = Router()


@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery) -> None:
    """
    Показывает последние операции по пользователю и его семье.
    """
    user_id = callback.from_user.id
    async with get_session() as session:
        user, family, entries = await get_history_for_user_with_family(
            session=session,
            user_id_or_telegram=user_id,
            limit=20,
        )

    lines = []
    if not entries:
        text = "История пуста"
    else:
        for e in entries:
            sign = "➕" if e.amount > 0 else "➖"
            owner = "Семья" if e.owner_type == OwnerType.FAMILY else "Вы"
            title = e.title or ""
            amount_abs = abs(int(e.amount))
            tail = f" · заказ #{e.order_id}" if e.order_id else ""
            lines.append(f"{sign} {owner}: {title} · {amount_abs}{tail}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=back_kb)
    await callback.answer()
