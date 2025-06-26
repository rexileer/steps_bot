from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from app.steps_bot.settings import config
from app.steps_bot.handlers import start
from app.steps_bot.handlers import back
from app.steps_bot.handlers import walk
from app.steps_bot.handlers import location

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(back.router)
dp.include_router(walk.router)
dp.include_router(location.router)