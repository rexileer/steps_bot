import re
import asyncio
from contextlib import suppress
from aiogram.types import Message, ReplyKeyboardRemove

from app.steps_bot.presentation.keyboards.simple_kb import phone_request_kb, main_menu_kb


def is_valid_email(text: str) -> bool:
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+', text.strip()))


async def send_temp_warning(message: Message, text: str, delay: float = 3.0):
    warn = await message.answer(text)
    async def auto_delete():
        await asyncio.sleep(delay)
        with suppress(Exception):
            await warn.delete()
    asyncio.create_task(auto_delete())


async def registration_dialog(message: Message):
    # TODO: message answer подтягивать из бд, результат регистрации в коммитить в бд
    
    await message.answer('Приветствуем, это steps_bot', reply_markup=phone_request_kb)
    name = message.from_user.first_name

    while True:
        msg: Message = yield
        if msg.contact and msg.contact.phone_number:
            phone = msg.contact.phone_number
            break
        await send_temp_warning(msg, '❌ Пожалуйста, используйте кнопку "📲 Поделиться номером телефона"')

    await message.answer('Введите ваш email:', reply_markup=ReplyKeyboardRemove())

    while True:
        msg: Message = yield
        if is_valid_email(msg.text):
            email = msg.text.strip()
            break
        await send_temp_warning(msg, '❌ Введите корректный email')

    result = (
        f"Приветствуем в step_bot, {name}!\nВы успешно авторизовались!\n\n"
        f"📧 Email: {email}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Информация о возможностях бота ..."
    )
    await message.answer(result, reply_markup=main_menu_kb)
