from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from app.steps_bot.settings import config
from app.steps_bot.handlers import start
from app.steps_bot.handlers import back
from app.steps_bot.handlers import walk
from app.steps_bot.handlers import family
from app.steps_bot.handlers import faq
from app.steps_bot.handlers import catalog
from app.steps_bot.handlers import balance
from app.steps_bot.handlers import dog_walk
from app.steps_bot.handlers import rolldog_walk
from app.steps_bot.handlers import roller_walk
from app.steps_bot.handlers import live_location
from app.steps_bot.handlers import end_walk
from app.steps_bot.handlers import buy
from app.steps_bot.handlers import promo

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(back.router)
dp.include_router(walk.router)
dp.include_router(family.router)
dp.include_router(faq.router)
dp.include_router(catalog.router)
dp.include_router(balance.router)
dp.include_router(dog_walk.router)
dp.include_router(live_location.router)
dp.include_router(rolldog_walk.router)
dp.include_router(roller_walk.router)
dp.include_router(end_walk.router)
dp.include_router(buy.router)
dp.include_router(promo.router)