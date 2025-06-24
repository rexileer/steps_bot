import asyncio

from sqlalchemy import select
from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models import User, UserAction
from app.steps_bot.dispatcher import bot


async def _get_user_ids_for_action(session, action_filter: str | None) -> list[int]:
    if not action_filter:
        result = await session.execute(select(User.tg_id))
    else:
        result = await session.execute(
            select(User.tg_id)
            .join(UserAction, User.id == UserAction.user_id)
            .where(UserAction.type == action_filter)
            .distinct()
        )
    return [row[0] for row in result.all()]


async def _broadcast_message(text: str, action_filter: str | None = None):
    async with get_session() as session:
        user_ids = await _get_user_ids_for_action(session, action_filter)
        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=user_id, text=text)
            except Exception:
                pass


def send_broadcast(text: str, action_filter: str | None = None):
    asyncio.run(_broadcast_message(text, action_filter))
