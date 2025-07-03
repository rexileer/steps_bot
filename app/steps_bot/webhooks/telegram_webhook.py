from fastapi import APIRouter, Request
from aiogram.types import Update
import logging

from app.steps_bot.dispatcher import bot, dp

router = APIRouter()


@router.post('/webhook')
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        logging.debug(f'Incoming update: {body}')
        update = Update.model_validate(body)
        await dp.feed_update(bot, update)
        logging.info(f'Update processed: {update.update_id}')
        return {'ok': True}
    except Exception as e:
        logging.error(f'Error in Telegram webhook: {e}')
        return {'ok': False}
