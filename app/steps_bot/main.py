import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.steps_bot.dispatcher import bot
from app.steps_bot.settings import config
from app.steps_bot.presentation.commands import set_default_commands
from app.steps_bot.webhooks import telegram_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Setting webhook...")
        await bot.set_webhook(config.WEBHOOK_URL)
        logger.info(f"Webhook set to: {config.WEBHOOK_URL}")
        await set_default_commands(bot)
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
    yield
    logger.info("Shutting down...")
    try:
        await bot.delete_webhook()
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

app.include_router(telegram_webhook.router)
