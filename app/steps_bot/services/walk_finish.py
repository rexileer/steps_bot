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
)

logger = logging.getLogger(__name__)


async def finish_walk(
    message: Message,
    *,
    target_message_id: int | None = None,
    user_id: int | None = None,
) -> None:
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
            # 1) Где мы вообще? (исключит «бот пишет в одну БД, админка читает из другой»)
            dbinfo = await s.execute(text("select current_database(), current_user"))
            db_name, db_user = dbinfo.first()
            logger.info("DB check: current_database=%s, current_user=%s", db_name, db_user)

            # 2) До апдейта: есть ли юзер с таким telegram_id?
            before = await s.execute(
                select(User.id, User.telegram_id, User.step_count, User.balance)
                .where(User.telegram_id == uid)
            )
            row_before = before.first()
            logger.info("Before update (by telegram_id=%s): %s", uid, row_before)

            # 3) Прямой апдейт по telegram_id
            upd = (
                update(User)
                .where(User.telegram_id == uid)
                .values(
                    step_count=User.step_count + total_steps,
                    balance=User.balance + points,
                    updated_at=finished_at,
                )
                .returning(User.id, User.telegram_id, User.step_count, User.balance)
            )
            res = await s.execute(upd)
            row_after = res.first()

            if row_after:
                logger.info(
                    "Updated by telegram_id: id=%s, tg=%s, step_count=%s, balance=%s",
                    row_after.id, row_after.telegram_id, row_after.step_count, row_after.balance
                )
            else:
                # 4) Фолбэк: а вдруг у тебя User.id == telegram_id
                logger.warning("No rows updated by telegram_id=%s, trying by id...", uid)
                upd2 = (
                    update(User)
                    .where(User.id == uid)
                    .values(
                        step_count=User.step_count + total_steps,
                        balance=User.balance + points,
                        updated_at=finished_at,
                    )
                    .returning(User.id, User.telegram_id, User.step_count, User.balance)
                )
                res2 = await s.execute(upd2)
                row_after2 = res2.first()
                logger.info("Updated by id result: %s", row_after2)

                # И ещё раз посмотрим, что лежит сейчас по обоим ключам
                after_tg = await s.execute(
                    select(User.id, User.telegram_id, User.step_count, User.balance)
                    .where(User.telegram_id == uid)
                )
                after_id = await s.execute(
                    select(User.id, User.telegram_id, User.step_count, User.balance)
                    .where(User.id == uid)
                )
                logger.info("After check by telegram_id: %s", after_tg.first())
                logger.info("After check by id: %s", after_id.first())

    except Exception as e:
        logger.exception("Failed to update user counters for %s: %s", uid, e)

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

    # Чистим времянки
    user_coords.pop(uid, None)
    user_was_over_speed.pop(uid, None)
    user_walk_multiplier.pop(uid, None)
    user_walk_form.pop(uid, None)
    user_walk_started_at.pop(uid, None)
    user_steps.pop(uid, None)
