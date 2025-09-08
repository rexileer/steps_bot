import asyncio
from contextlib import suppress

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.steps_bot.presentation.keyboards.simple_kb import no_family_kb, family_cancel_kb

from app.steps_bot.presentation.keyboards.generic_kb import build_owner_kb, invite_response_kb, build_member_kb
from app.steps_bot.services.family_service import FamilyService
from app.steps_bot.db.repo import get_session
from app.steps_bot.services.ledger_service import get_user_contribution_points
from app.steps_bot.states.family_creation import FamilyCreation
from app.steps_bot.states.family_invite import FamilyInvite
from app.steps_bot.states.family_rename import FamilyRename

router = Router()


async def flash(msg: Message, text: str, delay: float = 2):
    """Автоудаление предупреждений"""
    warn = await msg.answer(text)
    await asyncio.sleep(delay)
    with suppress(Exception):
        await warn.delete()
        

async def _show_family_menu(msg: Message, user_tg_id: int):
    (
        family,
        members,
        my_steps,
        my_balance,
        total_steps,
        total_balance,
    ) = await FamilyService.get_family_stats(user_tg_id)

    if not family:
        await msg.answer(
            "Вы пока не состоите в семье.",
            reply_markup=no_family_kb,
        )
        return
    
    owner_id   = members[0].id if members else 0

    lines = []
    for m in members:
        parts = [f"@{m.username}"]
        if m.telegram_id == user_tg_id:
            parts.append("(вы)")
        if m.id == owner_id:
            parts.append("(владелец)")
        lines.append("• " + " ".join(parts))

    members_block = "\n".join(lines) or "—"

    header = (
        f"💠 <b>{family.name}</b>\n\n"
        f"Семейные шаги: <b>{total_steps}</b>\n"
        f"Семейные баллы: <b>{total_balance}</b>\n\n"
        "Участники:"
    )

    is_owner = members and members[0].telegram_id == user_tg_id
    kb = (
        build_owner_kb(members, user_tg_id)
        if is_owner 
        else build_member_kb(members, user_tg_id, owner_id)
    )

    await msg.answer(header + "\n" + members_block, reply_markup=kb)


@router.callback_query(F.data == "family")
async def menu_family(callback: CallbackQuery):
    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "create_family")
async def ask_family_name(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает название семьи и показывает кнопку отмены.
    """
    await callback.message.edit_text("Введите название семьи:", reply_markup=family_cancel_kb)
    await state.set_state(FamilyCreation.waiting_for_name)
    await callback.answer()
    
    
@router.callback_query(F.data == "family_cancel_create", FamilyCreation.waiting_for_name)
async def cancel_family_creation(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет создание семьи и возвращает меню семьи.
    """
    await state.clear()
    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    await callback.answer("Отменено")


@router.message(FamilyCreation.waiting_for_name)
async def process_family_name(msg: Message, state: FSMContext):
    name = msg.text.strip()

    try:
        await FamilyService.create_family(msg.from_user.id, name)
    except ValueError as e:
        await flash(msg, f"⚠️ {e}")
        await state.clear()
        await _show_family_menu(msg, msg.from_user.id)
        return

    await flash(msg, "Семья создана!")
    await state.clear()
    await _show_family_menu(msg, msg.from_user.id)


@router.callback_query(F.data.startswith("family_kick:"))
async def kick_member(callback: CallbackQuery):
    member_id = int(callback.data.split(":")[1])
    try:
        await FamilyService.kick_member(callback.from_user.id, member_id)
        await callback.answer("Удалён")
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)

    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    

@router.callback_query(F.data == "family_invite")
async def ask_username(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите @username пользователя, которого хотите пригласить:")
    await state.set_state(FamilyInvite.waiting_for_username)
    await callback.answer()
    

@router.message(FamilyInvite.waiting_for_username)
async def do_invite(msg: Message, state: FSMContext):
    username = msg.text.lstrip("@").strip()

    try:
        invitation, family_name = await FamilyService.invite_user(
            msg.from_user.id, username
        )
    except ValueError as e:
        await flash(msg, f"⚠️ {e}")
        await state.clear()
        await _show_family_menu(msg, msg.from_user.id)
        return

    await flash(msg, "Приглашение отправлено")
    await state.clear()

    invitee = await FamilyService.get_member_by_db_id(invitation.invitee_id)
    if invitee:
        await msg.bot.send_message(
            invitee.telegram_id,
            f"@{msg.from_user.username} приглашает вас в семью «{family_name}».",
            reply_markup=invite_response_kb(invitation.id),
        )

    await _show_family_menu(msg, msg.from_user.id)
    

@router.callback_query(F.data.startswith("family_accept:"))
async def accept_invite(callback: CallbackQuery):
    inv_id = int(callback.data.split(":")[1])

    try:
        await FamilyService.respond_invitation(callback.from_user.id, inv_id, True)
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.message.edit_text("Вы вступили в семью.", reply_markup=None)
    await _show_family_menu(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("family_decline:"))
async def decline_invite(callback: CallbackQuery):
    inv_id = int(callback.data.split(":")[1])
    try:
        await FamilyService.respond_invitation(callback.from_user.id, inv_id, False)
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.message.edit_text("Приглашение отклонено.", reply_markup=None)
    await callback.answer()
    

@router.callback_query(F.data == "family_leave")
async def leave_family(callback: CallbackQuery):
    await FamilyService.leave_family(callback.from_user.id)
    await callback.answer("Вы вышли из семьи")
    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    

@router.callback_query(F.data == "disband")
async def disband(callback: CallbackQuery):
    try:
        await FamilyService.disband_family(callback.from_user.id)
        await callback.answer("Семья расформирована")
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    

@router.callback_query(F.data.startswith("family_info:"))
async def member_info(cb: CallbackQuery):
    member_id = int(cb.data.split(":")[1])
    member = await FamilyService.get_member_by_db_id(member_id)
    if not member:
        await cb.answer("Пользователь не найден", show_alert=True)
        return

    full_name = " ".join(filter(None, [member.first_name, member.last_name])).strip()

    # Баллы вклада: суммируем начисления пользователя по проводкам (шаги/промо)
    async with get_session() as session:
        contribution = await get_user_contribution_points(session, member.id)

    lines = [
        f"👤 @{member.username}",
        *( [f"Имя: {full_name}"] if full_name else [] ),
        f"Шаги: {member.step_count}",
        f"Вклад баллами: {contribution}",
    ]
    text = "\n".join(lines)

    await cb.answer(text, show_alert=True)
    

@router.callback_query(F.data == "family_rename")
async def ask_new_family_name(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает новое название семьи
    """
    await callback.message.edit_text(
        "Введите новое название семьи:", reply_markup=family_cancel_kb
    )
    await state.set_state(FamilyRename.waiting_for_name)
    await callback.answer()


@router.callback_query(
    F.data == "family_cancel_create", FamilyRename.waiting_for_name
)
async def cancel_family_rename(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет переименование семьи и возвращает меню семьи
    """
    await state.clear()
    await callback.message.delete()
    await _show_family_menu(callback.message, callback.from_user.id)
    await callback.answer("Отменено")


@router.message(FamilyRename.waiting_for_name)
async def process_new_family_name(msg: Message, state: FSMContext):
    """
    Обрабатывает новое название семьи
    """
    name = (msg.text or "").strip()

    try:
        await FamilyService.rename_family(msg.from_user.id, name)
    except ValueError as e:
        await flash(msg, f"⚠️ {e}")
        await state.clear()
        await _show_family_menu(msg, msg.from_user.id)
        return

    await flash(msg, "Название обновлено")
    await state.clear()
    await _show_family_menu(msg, msg.from_user.id)