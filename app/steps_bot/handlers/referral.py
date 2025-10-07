"""
Обработчики для реферальной системы
"""
import logging
from math import ceil

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.steps_bot.services.referral_service import (
    get_referral_stats,
    get_referrals_list,
    generate_referral_link,
)

router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 10  # Количество рефералов на странице


@router.callback_query(F.data == "referral_system")
async def show_referral_main(callback: CallbackQuery):
    """Показывает главный экран реферальной системы"""
    telegram_id = callback.from_user.id
    
    # Получаем статистику
    referral_count, earned_points = await get_referral_stats(telegram_id)
    
    # Получаем username бота для генерации ссылки
    bot: Bot = callback.bot
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    # Генерируем реферальную ссылку
    referral_link = await generate_referral_link(telegram_id, bot_username)
    
    # Формируем текст
    text = (
        f"🎁 <b>Реферальная система</b>\n\n"
        f"Ваша реферальная ссылка:\n"
        f"<code>{referral_link}</code>\n\n"
        f"👥 Количество рефералов: <b>{referral_count}</b>\n"
        f"💰 Заработано баллов: <b>{earned_points}</b>"
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Мои рефералы", callback_data="referral_list:0")
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("referral_list:"))
async def show_referral_list(callback: CallbackQuery):
    """Показывает список рефералов с пагинацией"""
    telegram_id = callback.from_user.id
    
    # Извлекаем номер страницы из callback_data
    page = int(callback.data.split(":")[1])
    offset = page * PAGE_SIZE
    
    # Получаем список рефералов
    referrals = await get_referrals_list(telegram_id, offset=offset, limit=PAGE_SIZE)
    
    if not referrals:
        text = "📭 У вас пока нет рефералов.\n\nПоделитесь своей реферальной ссылкой, чтобы пригласить друзей!"
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="referral_system")
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        return
    
    # Формируем текст со списком
    text_lines = ["👥 <b>Мои рефералы:</b>\n"]
    start_num = offset + 1
    
    for i, name in enumerate(referrals, start=start_num):
        text_lines.append(f"{i}. {name}")
    
    text = "\n".join(text_lines)
    
    # Создаем клавиатуру с пагинацией
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("◀️ Назад", f"referral_list:{page - 1}"))
    
    # Проверяем, есть ли еще рефералы
    if len(referrals) == PAGE_SIZE:
        nav_buttons.append(("Вперед ▶️", f"referral_list:{page + 1}"))
    
    if nav_buttons:
        for text_btn, callback_data in nav_buttons:
            builder.button(text=text_btn, callback_data=callback_data)
        builder.adjust(len(nav_buttons))
    
    # Кнопка возврата
    builder.button(text="◀️ К реферальной системе", callback_data="referral_system")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

