import asyncio
import logging

from app.steps_bot.dispatcher import dp, bot
from app.steps_bot.services.broadcast_service import run_broadcast_worker_once


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

    async def scheduler():
        while True:
            try:
                await run_broadcast_worker_once()
            except Exception as e:
                logging.error("broadcast worker error: %s", e)
            await asyncio.sleep(60)

    await asyncio.gather(
        dp.start_polling(bot),
        scheduler(),
    )


if __name__ == "__main__":
    asyncio.run(_main())



