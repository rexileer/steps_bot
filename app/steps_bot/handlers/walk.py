from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.simple_kb import walk_choice, location_kb

router = Router()


@router.callback_query(F.data == 'walk')
async def show_contacts(callback: CallbackQuery):
    await callback.message.edit_text(
        'Выберите опцию:',
        reply_markup=walk_choice
    )
    await callback.answer()
