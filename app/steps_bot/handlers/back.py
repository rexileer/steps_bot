from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.simple_kb import main_menu_kb
from app.steps_bot.services.captions_service import render

router = Router()


@router.callback_query(F.data == 'back')
async def show_contacts(callback: CallbackQuery):
    await callback.message.delete()
    await render(
        callback.message,
        "main_menu",  # slug для БД
        reply_markup=main_menu_kb,
    )
    await callback.answer()