from sqlalchemy import select
from typing import Optional, Tuple

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.faq import FAQ, FAQMediaType
from aiogram.types import Message, InlineKeyboardMarkup


async def get_faq(slug: str) -> Optional[Tuple[FAQ, str]]:
    async with get_session() as session:
        faq: FAQ | None = await session.scalar(select(FAQ).where(FAQ.slug == slug))
        if not faq:
            return None

        text = f"<b>{faq.question}</b>\n\n{faq.answer}"
        return faq, text


async def render_faq(
    message: Message,
    slug: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    res = await get_faq(slug)
    if not res:
        return await message.answer(
            f'Нет записи FAQ с ключом «{slug}»', reply_markup=reply_markup
        )

    faq, text = res

    if faq.media_type == FAQMediaType.PHOTO:
        if faq.telegram_file_id:
            return await message.answer_photo(
                faq.telegram_file_id, caption=text, reply_markup=reply_markup
            )
        if faq.media_url:
            return await message.answer_photo(
                faq.media_url, caption=text, reply_markup=reply_markup
            )

    if faq.media_type == FAQMediaType.VIDEO:
        if faq.telegram_file_id:
            return await message.answer_video(
                faq.telegram_file_id, caption=text, reply_markup=reply_markup
            )
        if faq.media_url:
            return await message.answer_video(
                faq.media_url, caption=text, reply_markup=reply_markup
            )

    return await message.answer(text, reply_markup=reply_markup)



async def get_all_faqs() -> list[FAQ]:
    async with get_session() as session:
        rows = await session.scalars(select(FAQ).order_by(FAQ.id))
        return list(rows)