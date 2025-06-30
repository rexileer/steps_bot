from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.simple_kb import walk_choice
from app.steps_bot.services.captions_service import render

router = Router()


@router.callback_query(F.data == 'walk')
async def show_contacts(callback: CallbackQuery):
    await callback.message.delete()
    await render(
        callback.message,
        "walk_choice",  # slug из БД
        reply_markup=walk_choice,
    )
    await callback.answer()
