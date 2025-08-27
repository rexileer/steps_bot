import contextlib
import logging
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.steps_bot.db.models.walk import WalkForm
from app.steps_bot.presentation.keyboards.simple_kb import (
    end_walk_kb,
    walk_back_kb,
    walk_choice,
)
from app.steps_bot.services.coefficients_service import get_total_multiplier
from app.steps_bot.services.weather_service import get_current_temp_c
from app.steps_bot.states.walk import WalkStates
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

router = Router()
logger = logging.getLogger(__name__)

DEFAULT_STEP_GOAL = 3000


@router.callback_query(F.data == "walk_roller")
async def ask_for_stroller_walk_location(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Запускает прогулку с коляской и просит отправить лайв-локацию. Показывает кнопку возврата.
    """
    await callback.message.delete()
    await callback.message.answer(
        "👶 Чтобы начать прогулку с коляской, открой меню вложений (📎) и отправь лайв-локацию.",
        reply_markup=walk_back_kb,
    )
    await state.set_state(WalkStates.waiting_for_roller_walk_location)
    await callback.answer()


@router.callback_query(WalkStates.waiting_for_roller_walk_location, F.data == "walk_back")
async def cancel_stroller_walk_location(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменяет ожидание локации и возвращает к выбору вида прогулки.
    """
    await state.clear()
    with contextlib.suppress(Exception):
        await callback.message.delete()
    await callback.message.answer("Выберите вид прогулки:", reply_markup=walk_choice)
    await callback.answer()


@router.message(WalkStates.waiting_for_roller_walk_location, F.location)
async def process_stroller_walk_location(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Принимает лайв-локацию, фиксирует старт прогулки и выводит статус.
    """
    location = message.location
    user_id = message.from_user.id

    user_walk_finished.pop(user_id, None)
    await state.update_data(step_goal=DEFAULT_STEP_GOAL)

    if not location.live_period:
        await message.answer("❌ Пожалуйста, отправь именно лайв-локацию через 📎")
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

    user_walk_form[user_id] = WalkForm.STROLLER
    multiplier = await get_total_multiplier(WalkForm.STROLLER, temp_c=temp_c)
    user_walk_multiplier[user_id] = multiplier
    user_walk_started_at[user_id] = time.time()

    temp_str = (
        f"{'+' if (temp_c is not None and temp_c >= 0) else ''}{temp_c}°C"
        if temp_c is not None
        else "н/д"
    )

    sent = await message.answer(
        f"{temp_str}\n"
        f"🚶 Вы прошли: 0 / {DEFAULT_STEP_GOAL} шагов\n"
        f"⭐ Баллы: 0 (коэфф: ×{multiplier})",
        reply_markup=end_walk_kb,
    )
    user_msg_id[user_id] = {"chat_id": message.chat.id, "message_id": sent.message_id}
    logger.info(
        "Начало прогулки (коляска) пользователя %s: message_id=%s; temp=%s; mul=%s",
        user_id,
        sent.message_id,
        temp_c,
        multiplier,
    )
    await state.clear()
