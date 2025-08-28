from __future__ import annotations

import os
from typing import Any, Optional, Tuple

from aiogram.types import FSInputFile
from sqlalchemy import select, update

from app.steps_bot.db.models.captions import Content, MediaType
from app.steps_bot.db.repo import get_session
from app.steps_bot.settings import config


def _abs_media_path(path: Optional[str]) -> Optional[str]:
    """
    Возвращает абсолютный путь к медиа-файлу с учётом MEDIA_ROOT.
    """
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(config.MEDIA_ROOT, path)


async def get_content(slug: str, **fmt: Any) -> Optional[Tuple[Content, str]]:
    """
    Возвращает кортеж (контент, отформатированный текст) по slug.
    """
    async with get_session() as session:
        result = await session.scalars(select(Content).where(Content.slug == slug))
        content = result.first()
        if not content:
            return None
        text = content.text.format(**fmt) if fmt else content.text
        return content, text


async def _cache_file_id(content_id: int, file_id: str) -> None:
    """
    Сохраняет telegram_file_id для последующих отправок без загрузки.
    """
    if not file_id:
        return
    async with get_session() as session:
        await session.execute(
            update(Content)
            .where(Content.id == content_id)
            .values(telegram_file_id=file_id)
        )


async def render(
    message,
    slug: str,
    reply_markup=None,
    **fmt: Any,
):
    """
    Отправляет контент по приоритету: file_id → локальный файл → URL → текст.
    """
    item = await get_content(slug, **fmt)
    if not item:
        return await message.answer(
            f'Не хватает ключа "{slug}", пожалуйста, добавьте описание в админ-панели',
            reply_markup=reply_markup,
        )

    content, text = item
    path = _abs_media_path(content.media_file)
    url = content.media_url

    if content.media_type == MediaType.PHOTO:
        if content.telegram_file_id:
            return await message.answer_photo(content.telegram_file_id, caption=text, reply_markup=reply_markup)
        if path and os.path.exists(path):
            sent = await message.answer_photo(FSInputFile(path), caption=text, reply_markup=reply_markup)
            if sent.photo:
                await _cache_file_id(content.id, sent.photo[-1].file_id)
            return sent
        if url:
            sent = await message.answer_photo(url, caption=text, reply_markup=reply_markup)
            if sent.photo:
                await _cache_file_id(content.id, sent.photo[-1].file_id)
            return sent
        return await message.answer(text, reply_markup=reply_markup)

    if content.media_type == MediaType.VIDEO:
        if content.telegram_file_id:
            return await message.answer_video(content.telegram_file_id, caption=text, reply_markup=reply_markup)
        if path and os.path.exists(path):
            sent = await message.answer_video(FSInputFile(path), caption=text, reply_markup=reply_markup)
            if sent.video:
                await _cache_file_id(content.id, sent.video.file_id)
            return sent
        if url:
            sent = await message.answer_video(url, caption=text, reply_markup=reply_markup)
            if sent.video:
                await _cache_file_id(content.id, sent.video.file_id)
            return sent
        return await message.answer(text, reply_markup=reply_markup)

    return await message.answer(text, reply_markup=reply_markup)
