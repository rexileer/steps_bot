from __future__ import annotations

import logging
import datetime as dt

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, text, update

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.walk import WalkForm
from app.steps_bot.db.models.user import User
from app.steps_bot.presentation.keyboards.simple_kb import back_kb
from app.steps_bot.storage.user_memory import (
    user_walk_multiplier,
    user_walk_form,
    user_walk_started_at,
    user_steps,
    user_coords,
    user_was_over_speed,
    user_msg_id,
    user_walk_finished,
    user_daily_steps_used,
    user_daily_steps_date,
)
from app.steps_bot.services.ledger_service import accrue_steps_points

logger = logging.getLogger(__name__)


async def finish_walk(
    message: Message,
    *,
    target_message_id: int | None = None,
    user_id: int | None = None,
) -> None:
    """
    Завершает прогулку: фиксирует шаги, начисляет баллы в журнал и обновляет счётчик шагов.
    """
    uid = (
        user_id
        if user_id is not None
        else (message.from_user.id if message.from_user and not message.from_user.is_bot else message.chat.id)
    )

    user_walk_finished[uid] = True

    total_steps = int(user_steps.get(uid, 0))
    multiplier = int(user_walk_multiplier.get(uid, 1))
    _walk_form = user_walk_form.get(uid, WalkForm.DOG)
    points = int(total_steps * multiplier)

    finished_at = dt.datetime.now(dt.timezone.utc)
    started_ts = user_walk_started_at.get(uid)
    _started_at = (
        dt.datetime.fromtimestamp(started_ts, tz=dt.timezone.utc)
        if started_ts is not None else finished_at
    )

    try:
        async with get_session() as s:
            await accrue_steps_points(
                session=s,
                user_id_or_telegram=uid,
                amount=points,
                title="Начисление за прогулку",
                description=f"Шаги: {total_steps}, коэффициент: ×{multiplier}",
            )

            upd_steps = (
                update(User)
                .where((User.telegram_id == uid) | (User.id == uid))
                .values(
                    step_count=User.step_count + total_steps,
                    updated_at=finished_at,
                )
            )
            await s.execute(upd_steps)

    except Exception as e:
        logger.exception("Failed to finalize walk for %s: %s", uid, e)

    # Обновляем дневной использованный лимит
    try:
        today = dt.date.today().isoformat()
        if user_daily_steps_date.get(uid) != today:
            user_daily_steps_date[uid] = today
            user_daily_steps_used[uid] = 0
        user_daily_steps_used[uid] = int(user_daily_steps_used.get(uid, 0)) + total_steps
    except Exception:
        pass

    summary_text = (
        "🏁 Прогулка завершена!\n\n"
        f"Итого шагов: {total_steps}\n"
        f"Начислено баллов: {points} (коэфф: ×{multiplier})"
    )

    msg_id = target_message_id or user_msg_id.get(uid, {}).get("message_id")
    try:
        if msg_id:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text=summary_text,
                reply_markup=back_kb,
            )
        else:
            await message.answer(summary_text, reply_markup=back_kb)
    except TelegramBadRequest as e:
        logger.warning("finish_walk edit failed: %s", e)
        try:
            await message.answer(summary_text, reply_markup=back_kb)
        except Exception as e2:
            logger.exception("Fallback answer failed: %s", e2)

    user_coords.pop(uid, None)
    user_was_over_speed.pop(uid, None)
    user_walk_multiplier.pop(uid, None)
    user_walk_form.pop(uid, None)
    user_walk_started_at.pop(uid, None)
    user_steps.pop(uid, None)
