from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.steps_bot.db.models.user import User


# Меню овнера семьи
def build_owner_kb(members: List[User], me_tg_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Добавить участников", callback_data="family_invite")]]

    for m in members:
        tag = "👁 " if m.telegram_id == me_tg_id else "👁 "
        label = f"{tag}@{m.username}"

        row = [InlineKeyboardButton(text=label, callback_data=f"family_info:{m.id}")]

        if m.telegram_id != me_tg_id:
            row.append(
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"family_kick:{m.id}")
            )

        rows.append(row)

    rows += [
        [InlineKeyboardButton(text="Расформировать", callback_data="disband")],
        [InlineKeyboardButton(text="↩", callback_data="back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Меню принятия приглашения в семью
def invite_response_kb(inv_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Принять", callback_data=f"family_accept:{inv_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"family_decline:{inv_id}"),
            ]
        ]
    )


# Меню обычного участника
def build_member_kb(
    members: List[User],
    me_tg_id: int,
    owner_id: int,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Добавить участников", callback_data="family_invite")]]

    for m in members:
        tag = "👁 " if m.id == owner_id else "👁 "
        label = f"{tag}@{m.username}"
        
        row = [InlineKeyboardButton(text=label, callback_data=f"family_info:{m.id}")]

        if m.id != owner_id:
            row.append(InlineKeyboardButton(text="❌ Удалить", callback_data=f"family_kick:{m.id}"))

        rows.append(row)

    rows += [
        [InlineKeyboardButton(text="Выйти из семьи", callback_data="family_leave")],
        [InlineKeyboardButton(text="↩", callback_data="back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)