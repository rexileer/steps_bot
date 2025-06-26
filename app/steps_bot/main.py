import asyncio
import logging

from app.steps_bot.dispatcher import dp, bot
from app.steps_bot.presentation.commands import set_default_commands

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    logger.info("Start bot")
    await set_default_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")