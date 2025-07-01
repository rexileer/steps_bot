from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.services.faq_service import get_all_faqs
from app.steps_bot.presentation.keyboards.generic_kb import faq_list_kb, faq_back_kb
from app.steps_bot.services.faq_service import render_faq

router = Router()


@router.callback_query(F.data == "faq")
async def faq_menu(callback: CallbackQuery):
    faqs = await get_all_faqs()
    if not faqs:
        await callback.answer("FAQ пока пуст", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer(
        "Выберите вопрос:",
        reply_markup=faq_list_kb(faqs, page=1),
    )
    await callback.answer()
    

@router.callback_query(F.data.startswith("faq_page:"))
async def faq_page(callback: CallbackQuery):
    page = int(callback.data.split(":", 1)[1])
    faqs = await get_all_faqs()
    await callback.message.edit_reply_markup(reply_markup=faq_list_kb(faqs, page))
    await callback.answer()


@router.callback_query(F.data.startswith("faq_show:"))
async def faq_item(callback: CallbackQuery):
    slug = callback.data.split(":", 1)[1]
    await callback.message.delete()
    await render_faq(callback.message, slug, reply_markup=faq_back_kb)
    await callback.answer()
