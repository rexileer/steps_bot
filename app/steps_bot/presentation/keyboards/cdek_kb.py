from typing import Dict, List
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def pvz_list_kb(items: List[Dict], page: int, city_code: int) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру выбора ПВЗ по списку точек."""
    kb = InlineKeyboardBuilder()

    for it in items:
        code = it.get("code", "")
        addr = it.get("location", {}).get("address", "Адрес не указан")
        title = f"📍 {addr}"
        if len(title) > 64:
            title = title[:61] + "..."
        kb.button(text=title, callback_data=f"pvz:{code}")

    kb.adjust(1)

    nav: List[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"pvz_page:{city_code}:{page-1}"))
    if len(items) >= 10:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"pvz_page:{city_code}:{page+1}"))
    if nav:
        kb.row(*nav)

    return kb
