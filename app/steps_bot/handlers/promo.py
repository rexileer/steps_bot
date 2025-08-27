from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.presentation.keyboards.generic_kb import promo_groups_kb
from app.steps_bot.services.promo_service import list_active_groups, purchase_and_acquire_code_family
from app.steps_bot.services.captions_service import render

router = Router()


@router.callback_query(F.data == "promo_stub")
async def show_promo_menu(cb: CallbackQuery) -> None:
    """
    Удаляет предыдущее сообщение и показывает меню групп промокодов.
    """
    groups = await list_active_groups()
    if not groups:
        await cb.answer("Промокоды временно недоступны", show_alert=True)
        return

    kb = promo_groups_kb(groups)
    await cb.message.delete()
    try:
        await render(cb.message, "promo_intro", reply_markup=kb)
    except Exception:
        await cb.message.answer("Выберите группу промокодов:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.func(lambda v: v.startswith("promo_group:")))
async def give_promo_code(cb: CallbackQuery) -> None:
    """
    Покупает и выдаёт промокод из выбранной группы за баллы семьи.
    Показывает размер списания в баллах.
    """
    try:
        group_id = int(cb.data.split(":")[1])
    except Exception:
        await cb.answer("Некорректная группа", show_alert=True)
        return

    code, group, err = await purchase_and_acquire_code_family(group_id, cb.from_user.id)
    if err:
        await cb.answer(err, show_alert=True)
        return

    spent = int(getattr(group, "price_points", 0) or 0)
    await cb.message.answer(
        f'Ваш промокод: <code>{code}</code>\nСкидка: {group.discount_percent}%\nСписано: {spent} баллов',
        parse_mode="HTML",
    )
    await cb.answer()
