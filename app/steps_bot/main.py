import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.steps_bot.dispatcher import bot
from app.steps_bot.settings import config
from app.steps_bot.presentation.commands import set_default_commands
from app.steps_bot.webhooks.telegram_webhook import router as telegram_router
from app.steps_bot.webapps.router import router as webapps_router, mount_static

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info('Setting webhook...')
    await bot.set_webhook(config.WEBHOOK_URL)
    logging.info(f'Webhook set to: {config.WEBHOOK_URL}')
    await set_default_commands(bot)
    yield
    logging.info('Shutting down...')
    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)
app.include_router(telegram_router)
app.include_router(webapps_router)
mount_static(app)