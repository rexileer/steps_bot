import logging
import time

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.steps_bot.states.walk import WalkStates
from app.steps_bot.presentation.keyboards.simple_kb import end_walk_kb
from app.steps_bot.storage.user_memory import (
    user_coords,
    user_steps,
    user_msg_id,
    user_walk_finished,
    user_walk_multiplier,
    user_walk_form,
    user_walk_started_at,
    user_temp_c,
    user_temp_updated_at,
)
from app.steps_bot.db.models.walk import WalkForm
from app.steps_bot.services.coefficients_service import get_total_multiplier
from app.steps_bot.services.weather_service import get_current_temp_c

router = Router()
logger = logging.getLogger(__name__)

DEFAULT_STEP_GOAL = 3000


@router.callback_query(F.data == "walk_rolldog")
async def ask_for_stroller_dog_walk_location(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Нажатие «Гуляю с собакой и коляской». Просим отправить лайв-локацию.
    """
    await callback.message.delete()
    await callback.message.answer(
        "🐶👶 Чтобы начать прогулку с собакой и коляской, открой меню вложений (📎) и "
        "отправь лайв-локацию."
    )
    await state.set_state(WalkStates.waiting_for_rolldog_walk_location)
    await callback.answer()


@router.message(WalkStates.waiting_for_rolldog_walk_location, F.location)
async def process_stroller_dog_walk_location(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Принимаем live-локацию, фиксируем нулевую точку и стартуем счётчик.
    """
    location = message.location
    user_id = message.from_user.id

    user_walk_finished.pop(user_id, None)
    await state.update_data(step_goal=DEFAULT_STEP_GOAL)

    if not location.live_period:
        await message.answer("❌ Пожалуйста, отправь именно *лайв*-локацию через 📎")
        return

    user_coords.pop(user_id, None)
    user_steps.pop(user_id, None)
    user_msg_id.pop(user_id, None)

    current_coords = (location.latitude, location.longitude)
    user_coords[user_id] = (current_coords, time.time())
    user_steps[user_id] = 0

    temp_c = await get_current_temp_c(current_coords[0], current_coords[1])
    user_temp_c[user_id] = temp_c
    user_temp_updated_at[user_id] = time.time()

    user_walk_form[user_id] = WalkForm.STROLLER_DOG
    multiplier = await get_total_multiplier(WalkForm.STROLLER_DOG, temp_c=temp_c)
    user_walk_multiplier[user_id] = multiplier
    user_walk_started_at[user_id] = time.time()

    temp_str = f"{'+' if (temp_c is not None and temp_c >= 0) else ''}{temp_c}°C" if temp_c is not None else "н/д"
    temp_line = f"{temp_str}"

    sent = await message.answer(
        f"{temp_line}\n"
        f"🚶 Вы прошли: 0 / {DEFAULT_STEP_GOAL} шагов\n"
        f"⭐ Баллы: 0 (коэфф: ×{multiplier})",
        reply_markup=end_walk_kb,
    )
    user_msg_id[user_id] = {
        "chat_id": message.chat.id,
        "message_id": sent.message_id,
    }
    logger.info(
        "Начало прогулки (собака+коляска) пользователя %s: message_id=%s; temp=%s; mul=%s",
        user_id,
        sent.message_id,
        temp_c,
        multiplier,
    )

    await state.clear()
