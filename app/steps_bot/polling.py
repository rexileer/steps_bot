import asyncio
import logging

from app.steps_bot.dispatcher import dp, bot


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Убираем вебхук, чтобы переключиться на polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.warning("delete_webhook failed: %s", e)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(_main())


