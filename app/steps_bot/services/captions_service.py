from typing import Any, Tuple, Optional

from sqlalchemy import select

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.captions import Content, MediaType


async def get_content(slug: str, **fmt: Any) -> Optional[Tuple[Content, str]]:
    async with get_session() as session:
        result = await session.scalars(select(Content).where(Content.slug == slug))
        content = result.first()
        if not content:
            return None
        text = content.text.format(**fmt) if fmt else content.text
        return content, text


async def render(
    message,
    slug: str,
    reply_markup=None,
    **fmt: Any,
):
    item = await get_content(slug, **fmt)
    if not item:
        return await message.answer(
            f'Не хватает ключа "{slug}", пожалуйста, добавьте описание в админ-панели',
            reply_markup=reply_markup,
        )

    content, text = item
    file_or_url = content.telegram_file_id or content.media_url

    if content.media_type == MediaType.PHOTO and file_or_url:
        return await message.answer_photo(file_or_url, caption=text, reply_markup=reply_markup)

    if content.media_type == MediaType.VIDEO and file_or_url:
        return await message.answer_video(file_or_url, caption=text, reply_markup=reply_markup)

    return await message.answer(text, reply_markup=reply_markup)