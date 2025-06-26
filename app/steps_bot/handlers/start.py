import re
import asyncio

from contextlib import suppress
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.steps_bot.presentation.keyboards.simple_kb import phone_kb, main_menu_kb
from app.steps_bot.states.registration import Registration

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
    # TODO: message.answer тянуть из бд
    
    await message.answer('Приветствуем, это steps_bot', reply_markup=phone_kb)
    await state.set_state(Registration.waiting_for_phone)


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
    # TODO: message.answer тянуть из бд
    await state.update_data(email=message.text.strip())
    data = await state.get_data()

    name = message.from_user.first_name
    phone = data.get('phone')
    email = data.get('email')

    await message.answer(
        f"Приветствуем в step_bot, {name}!\nВы успешно авторизовались!\n\n"
        f"📧 Email: {email}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Информация о возможностях бота ...",
        reply_markup=main_menu_kb
    )
    await state.clear()


@router.message(Registration.waiting_for_email)
async def warning_email(message: Message):
    await send_temp_warning(message, '❌ Введите корректный email')