from __future__ import annotations

from typing import List, Tuple, Optional

from sqlalchemy import select, func

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.catalog import CatalogCategory, Product
from app.steps_bot.db.models.captions import MediaType

from aiogram.types import Message, InlineKeyboardMarkup


async def get_categories() -> List[CatalogCategory]:
    async with get_session() as s:
        result = await s.scalars(select(CatalogCategory).order_by(CatalogCategory.name))
        return list(result)


async def get_category_page(
    cat_id: int,
    page: int,
    per_page: int,
) -> Tuple[List[Product], int]:
    async with get_session() as s:
        total = await s.scalar(
            select(func.count())
            .select_from(
                select(Product.id)
                .where(
                    Product.category_id == cat_id,
                    Product.is_active.is_(True),
                )
                .subquery()
            )
        ) or 0

        items_q = (
            select(Product)
            .where(
                Product.category_id == cat_id,
                Product.is_active.is_(True),
            )
            .order_by(Product.title)
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
        items = list(await s.scalars(items_q))
        return items, total


async def get_product(prod_id: int) -> Optional[Product]:
    async with get_session() as s:
        return await s.get(Product, prod_id)


async def render_product(
    message: Message,
    prod_id: int,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    product = await get_product(prod_id)
    if not product or not product.is_active:
        await message.answer("⚠️ Товар недоступен", reply_markup=reply_markup)
        return

    text = (
        f"<b>{product.title}</b>\n\n"
        f"{product.description}\n\n"
        f"<b>{product.price} баллов</b>"
    )

    if product.media_type == MediaType.PHOTO:
        if product.telegram_file_id:
            await message.answer_photo(product.telegram_file_id, caption=text, reply_markup=reply_markup)
            return
        if product.media_url:
            await message.answer_photo(product.media_url, caption=text, reply_markup=reply_markup)
            return

    if product.media_type == MediaType.VIDEO:
        if product.telegram_file_id:
            await message.answer_video(product.telegram_file_id, caption=text, reply_markup=reply_markup)
            return
        if product.media_url:
            await message.answer_video(product.media_url, caption=text, reply_markup=reply_markup)
            return

    await message.answer(text, reply_markup=reply_markup)
