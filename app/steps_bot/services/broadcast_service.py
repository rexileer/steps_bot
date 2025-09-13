import asyncio
from typing import Optional
import os

from sqlalchemy import select, func
from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models import User, Broadcast, BroadcastStatus, MediaType
from app.steps_bot.dispatcher import bot
from app.steps_bot.settings import config
from aiogram.types import FSInputFile


async def list_recipients(session) -> list[int]:
    result = await session.execute(select(User.telegram_id))
    return [row[0] for row in result.all()]


async def send_broadcast_now(b: Broadcast) -> None:
    async with get_session() as session:
        user_ids = await list_recipients(session)
    for uid in user_ids:
        try:
            if b.media_type == MediaType.PHOTO:
                # порядок: file_id -> локальный файл -> URL -> текст
                if b.telegram_file_id:
                    await bot.send_photo(uid, b.telegram_file_id, caption=b.text or "")
                else:
                    path = b.media_file
                    if path and not os.path.isabs(path):
                        path = os.path.join(config.MEDIA_ROOT, path)
                    if path and os.path.exists(path):
                        await bot.send_photo(uid, FSInputFile(path), caption=b.text or "")
                    elif b.media_url:
                        await bot.send_photo(uid, b.media_url, caption=b.text or "")
                    else:
                        await bot.send_message(uid, b.text or "")
            elif b.media_type == MediaType.VIDEO:
                if b.telegram_file_id:
                    await bot.send_video(uid, b.telegram_file_id, caption=b.text or "")
                else:
                    path = b.media_file
                    if path and not os.path.isabs(path):
                        path = os.path.join(config.MEDIA_ROOT, path)
                    if path and os.path.exists(path):
                        await bot.send_video(uid, FSInputFile(path), caption=b.text or "")
                    elif b.media_url:
                        await bot.send_video(uid, b.media_url, caption=b.text or "")
                    else:
                        await bot.send_message(uid, b.text or "")
            else:
                await bot.send_message(uid, b.text or "")
        except Exception:
            continue


async def pick_due_broadcast() -> Optional[Broadcast]:
    async with get_session() as session:
        q = select(Broadcast).where(Broadcast.status == BroadcastStatus.PENDING)
        # Если указано время — отправлять, когда наступило
        q = q.where((Broadcast.scheduled_at.is_(None)) | (Broadcast.scheduled_at <= func.now()))
        row = await session.execute(q.order_by(Broadcast.scheduled_at.is_(None).desc(), Broadcast.scheduled_at.asc()).limit(1))
        return row.scalar_one_or_none()


async def run_broadcast_worker_once() -> None:
    b = await pick_due_broadcast()
    if not b:
        return
    await send_broadcast_now(b)
    async with get_session() as session:
        db_b = await session.get(Broadcast, b.id)
        if db_b:
            db_b.status = BroadcastStatus.SENT
