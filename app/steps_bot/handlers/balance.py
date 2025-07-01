from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.simple_kb import balance_kb
from app.steps_bot.services.family_service import FamilyService

router = Router()


@router.callback_query(F.data == 'balance')
async def show_balance(callback: CallbackQuery):
    await callback.message.delete()

    user_id = callback.from_user.id
    (
        family,
        members,
        my_steps,
        my_balance,
        total_steps,
        total_balance,
    ) = await FamilyService.get_family_stats(user_id)

    text = (
        f"<b>Ваши баллы:</b> {my_balance}\n"
        f"<b>Баллы семьи:</b> {total_balance}"
    )

    await callback.message.answer(text, reply_markup=balance_kb)
    await callback.answer()

