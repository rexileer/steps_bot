from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.simple_kb import main_menu_kb

router = Router()


@router.callback_query(F.data == 'back')
async def show_contacts(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        'Описание возможностей бота ...:',
        reply_markup=main_menu_kb
    )
    await callback.answer()