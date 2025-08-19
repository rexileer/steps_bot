import logging
import time

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.steps_bot.services.step_counter import (
    calculate_steps,
    is_too_fast,
    calculate_distance_m,
)
from app.steps_bot.services.walk_finish import finish_walk
from app.steps_bot.services.weather_service import get_current_temp_c
from app.steps_bot.services.coefficients_service import get_total_multiplier
from app.steps_bot.storage.user_memory import (
    user_coords,
    user_steps,
    user_msg_id,
    user_was_over_speed,
    user_walk_finished,
    user_walk_multiplier,
    user_walk_form,
    user_temp_c,
    user_temp_updated_at,
)
from app.steps_bot.handlers.dog_walk import DEFAULT_STEP_GOAL
from app.steps_bot.presentation.keyboards.simple_kb import end_walk_kb

router = Router()
logger = logging.getLogger(__name__)

TEMP_REFRESH_SECONDS = 180


@router.edited_message(F.location)
async def handle_live_location_update(message: Message, state: FSMContext) -> None:
    """Обрабатывает каждое live-обновление геолокации и ведёт подсчёт шагов и баллов."""
    user_id = message.from_user.id
    if user_walk_finished.get(user_id):
        return

    location = message.location
    data = await state.get_data()
    step_goal: int = data.get("step_goal", DEFAULT_STEP_GOAL)

    if not location or not location.live_period:
        return

    curr_coords = (location.latitude, location.longitude)
    curr_ts = time.time()

    prev_data = user_coords.get(user_id)
    if not prev_data:
        user_coords[user_id] = (curr_coords, curr_ts)
        return

    prev_coords, prev_ts = prev_data
    distance_m = calculate_distance_m(prev_coords, curr_coords)
    delta_t = curr_ts - prev_ts
    speed_kmh = (distance_m / delta_t) * 3.6 if delta_t > 0 else 0.0

    if is_too_fast(prev_coords, curr_coords, prev_ts, curr_ts):
        user_was_over_speed[user_id] = True
        warning = "⚠️ Скорость слишком высокая, шаги не учитываются"
        total_steps = user_steps.get(user_id, 0)
    else:
        steps = calculate_steps(prev_coords, curr_coords)
        if user_was_over_speed.get(user_id):
            user_was_over_speed[user_id] = False
        if steps > 0:
            user_steps[user_id] = user_steps.get(user_id, 0) + steps
        warning = None
        total_steps = user_steps[user_id]

    if total_steps >= step_goal:
        if total_steps > step_goal:
            user_steps[user_id] = step_goal
            total_steps = step_goal

        msg_data = user_msg_id.get(user_id)
        if msg_data:
            await finish_walk(message, target_message_id=msg_data["message_id"])
        return

    last_temp_ts = user_temp_updated_at.get(user_id)
    need_refresh = last_temp_ts is None or (curr_ts - last_temp_ts) >= TEMP_REFRESH_SECONDS
    if need_refresh:
        try:
            fresh_temp = await get_current_temp_c(curr_coords[0], curr_coords[1])
        except Exception:
            fresh_temp = None
        if fresh_temp is not None:
            user_temp_c[user_id] = fresh_temp
            user_temp_updated_at[user_id] = curr_ts
            form = user_walk_form.get(user_id)
            if form is not None:
                try:
                    user_walk_multiplier[user_id] = await get_total_multiplier(form, temp_c=fresh_temp)
                except Exception:
                    logger.exception("Не удалось пересчитать множитель")

    temp_c = user_temp_c.get(user_id)
    multiplier = user_walk_multiplier.get(user_id, 1)
    points = total_steps * multiplier

    temp_str = f"{'+' if (temp_c is not None and temp_c >= 0) else ''}{temp_c}°C" if temp_c is not None else "н/д"
    temp_line = f"{temp_str}"

    text_parts = [
        temp_line,
        f"🚶 Вы прошли: {total_steps} / {step_goal} шагов",
        f"⭐ Баллы: {points} (коэфф: ×{multiplier})",
        f"📏 Скорость: {speed_kmh:.1f} км/ч",
    ]
    if warning:
        text_parts.append(f"\n{warning}")
    new_text = "\n".join(text_parts)

    msg_data = user_msg_id.get(user_id)
    if msg_data:
        try:
            await message.bot.edit_message_text(
                chat_id=msg_data["chat_id"],
                message_id=msg_data["message_id"],
                text=new_text,
                reply_markup=end_walk_kb,
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                sent = await message.answer(new_text, reply_markup=end_walk_kb)
                user_msg_id[user_id] = {
                    "chat_id": message.chat.id,
                    "message_id": sent.message_id,
                }

    user_coords[user_id] = (curr_coords, curr_ts)
