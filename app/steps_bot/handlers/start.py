import re
import asyncio

from contextlib import suppress
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.steps_bot.presentation.keyboards.simple_kb import phone_kb, main_menu_kb, accept_kb
from app.steps_bot.states.registration import Registration
from app.steps_bot.services.user_service import register_user, get_user, sync_username
from app.steps_bot.services.captions_service import render

router = Router()


def is_valid_email(text: str) -> bool:
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+', text.strip()))


async def send_temp_warning(message: Message, text: str, delay: float = 3.0):
    """Автоудаление сообщений-предупреждений"""

    warn = await message.answer(text)

    async def auto_delete():
        await asyncio.sleep(delay)
        with suppress(Exception):
            await warn.delete()

    asyncio.create_task(auto_delete())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Показываем главное меню сразу, если пользователь уже зарегистрирован."""

    await sync_username(message.from_user.id, message.from_user.username)
    user = await get_user(message.from_user.id)

    if user and user.phone and user.email:
        await render(
            message,
            "main_menu",  # slug из БД
            reply_markup=main_menu_kb,
            name=message.from_user.first_name,
            phone=user.phone,
            email=user.email,
        )
        await state.clear()
        return

    await render(message, "start_welcome", reply_markup=accept_kb)  # slug из БД
    await state.set_state(Registration.waiting_for_phone)


@router.callback_query(F.data == "accept")
async def accept_pd(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await cb.message.answer("Пожалуйста, отправьте свой номер телефона:",
                            reply_markup=phone_kb)
    await state.set_state(Registration.waiting_for_phone)
    await cb.answer()


@router.message(Registration.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer('Введите ваш email:', reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.waiting_for_email)


@router.message(Registration.waiting_for_phone)
async def warning_phone(message: Message):
    await send_temp_warning(message, '❌ Пожалуйста, используйте кнопку')


@router.message(Registration.waiting_for_email, F.text.func(is_valid_email))
async def process_email(message: Message, state: FSMContext):
    """Message берется из БД"""
        
    await state.update_data(email=message.text.strip())
    data = await state.get_data()

    name = message.from_user.first_name
    phone = data.get('phone')
    email = data.get('email')

    await register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        phone=phone,
        email=email,
    )

    await render(
        message,
        "main_menu",  # slug для БД
        reply_markup=main_menu_kb,
        name=name,
        phone=phone,
        email=email,
    )
    await state.clear()


@router.message(Registration.waiting_for_email)
async def warning_email(message: Message):
    await send_temp_warning(message, '❌ Введите корректный email')
