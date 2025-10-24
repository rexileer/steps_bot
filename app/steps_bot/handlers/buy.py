from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import Any

from app.steps_bot.services.buy_service import (
    finalize_successful_order,
    format_order_message,
    load_product_summary,
    ensure_purchase_allowed,
)
from app.steps_bot.db import repo
from app.steps_bot.services.validators import (
    normalize_phone,
    validate_address,
    validate_city,
    validate_full_name,
    validate_phone,
    validate_pvz_code,
)
from app.steps_bot.states.order import OrderInput, OrderStates


router = Router()


def pvz_list_kb(items: list[Any], page: int = 0) -> InlineKeyboardBuilder:
    """
    Возвращает клавиатуру выбора ПВЗ из локального списка.
    
    Args:
        items: список объектов PVZ из БД
        page: номер страницы (для совместимости)
    """
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=f"📍 {item.full_address[:40]}", callback_data=f"pvz:{item.id}")
    kb.adjust(1)
    return kb


def delivery_type_kb(return_cb: str | None = None) -> InlineKeyboardBuilder:
    """
    Клавиатура выбора типа доставки: только ПВЗ + назад к товарам.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="Яндекс.Доставка", callback_data="order:delivery:pvz")
    kb.button(text="↩", callback_data=return_cb or "catalog_root")
    kb.adjust(1, 1)
    return kb


def back_to_delivery_kb() -> InlineKeyboardBuilder:
    """
    Возвращает клавиатуру с кнопкой возврата к выбору типа доставки.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="↩", callback_data="order:back")
    kb.adjust(1)
    return kb


def confirm_kb() -> InlineKeyboardBuilder:
    """
    Возвращает клавиатуру подтверждения заказа.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить", callback_data="order:confirm")
    kb.button(text="Отменить", callback_data="order:cancel")
    kb.button(text="↩", callback_data="order:back")
    kb.adjust(2, 1)
    return kb


def _extract_return_cb(markup: InlineKeyboardMarkup | None) -> str:
    """
    Извлекает колбэк кнопки «назад к товарам» из предыдущей клавиатуры.
    Ищет кнопку с callback_data, начинающимся на 'cat:'.
    Если не найдено — возвращает 'catalog_root'.
    """
    if not markup or not getattr(markup, "inline_keyboard", None):
        return "catalog_root"
    for row in markup.inline_keyboard:
        for btn in row:
            data = getattr(btn, "callback_data", None)
            if isinstance(data, str) and data.startswith("cat:"):
                return data
    return "catalog_root"


def _extract_product_id(data: dict[str, Any]) -> int | None:
    """
    Достаёт product_id из состояния и валидирует тип.
    Возвращает None, если идентификатор отсутствует.
    """
    value = data.get("product_id")
    return value if isinstance(value, int) else None


@router.callback_query(F.data.startswith("buy:"))
async def on_buy_click(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Инициирует процесс оформления заказа и запускает сбор данных.
    """
    try:
        _, product_id_str = callback.data.split(":")
        product_id = int(product_id_str)
        await state.update_data(product_id=product_id)
    except Exception:
        await callback.answer("Ошибка данных товара", show_alert=True)
        return

    allowed, msg = await ensure_purchase_allowed(callback.from_user.id, product_id)
    if not allowed:
        await callback.answer(msg, show_alert=True)
        return

    return_cb = _extract_return_cb(callback.message.reply_markup)

    await state.set_state(OrderStates.choosing_delivery_type)
    await callback.message.delete()
    await callback.message.answer(
        "Выберите тип доставки:",
        reply_markup=delivery_type_kb(return_cb).as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "order:back")
async def on_back_to_delivery(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возвращает к выбору типа доставки, сохраняя выбранный товар.
    """
    data = await state.get_data()
    product_id = int(data.get("product_id")) if data and data.get("product_id") else None
    await state.clear()
    if product_id is not None:
        await state.update_data(product_id=product_id)
    await state.set_state(OrderStates.choosing_delivery_type)
    await callback.message.edit_text(
        "Выберите тип доставки:",
        reply_markup=delivery_type_kb().as_markup(),
    )
    await callback.answer()


@router.callback_query(
    OrderStates.choosing_delivery_type,
    F.data == "order:delivery:pvz",
)
async def on_delivery_type(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохраняет тип доставки (ПВЗ) и запрашивает город.
    """
    await state.update_data(delivery_type="pvz")
    await state.set_state(OrderStates.entering_city)
    await callback.message.edit_text(
        "Укажите город получателя (например: Москва):",
        reply_markup=back_to_delivery_kb().as_markup(),
    )
    await callback.answer()


@router.message(OrderStates.entering_city, F.text.len() > 0)
async def on_city_entered(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает ввод города.
    Если ПВЗ <= 10, показывает их сразу.
    Если ПВЗ > 10, просит уточнить улицу.
    """
    city = message.text.strip()
    if not validate_city(city):
        await message.answer("Город указан некорректно. Повторите ввод.", reply_markup=back_to_delivery_kb().as_markup())
        return

    # Получаем ПВЗ из локальной БД
    try:
        async with repo.get_session() as session:
            pvz_list = await repo.get_pvz_by_city(session, city)
    except Exception as e:
        await message.answer(
            f"Ошибка при получении списка ПВЗ: {escape(str(e))}",
            reply_markup=back_to_delivery_kb().as_markup()
        )
        return

    if not pvz_list:
        await message.answer(
            "К сожалению нет доступных ПВЗ по указанному адресу.",
            reply_markup=back_to_delivery_kb().as_markup()
        )
        return

    await state.update_data(city=city)

    # Если ПВЗ 10 или меньше - показываем сразу
    if len(pvz_list) <= 10:
        kb = pvz_list_kb(pvz_list)
        kb.button(text="↩", callback_data="order:back")
        await message.answer(
            "Выберите пункт выдачи:",
            reply_markup=kb.as_markup(),
        )
        await state.set_state(OrderStates.entering_pvz_or_address)
    else:
        # Если больше 10 - просим уточнить улицу
        await message.answer(
            "Укажите улицу получателя (например: Ленина):"
        )
        await state.set_state(OrderStates.entering_street)


@router.message(OrderStates.entering_street, F.text.len() > 0)
async def on_street_entered(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает ввод улицы и фильтрует ПВЗ.
    """
    street = message.text.strip()
    if not street or len(street) < 2:
        await message.answer("Пожалуйста, укажите улицу подробнее (минимум 2 символа).")
        return

    data = await state.get_data()
    city = data.get("city")

    if not city:
        await message.answer("Сессия устарела, начните заново.", reply_markup=back_to_delivery_kb().as_markup())
        return

    # Получаем ПВЗ, отфильтрованные по городу и улице
    try:
        async with repo.get_session() as session:
            pvz_list = await repo.get_pvz_by_city_and_street(session, city, street)
    except Exception as e:
        await message.answer(
            f"Ошибка при получении списка ПВЗ: {escape(str(e))}",
            reply_markup=back_to_delivery_kb().as_markup()
        )
        return

    if not pvz_list:
        await message.answer(
            "ПВЗ не найдены по этому адресу. Попробуйте другой адрес или начните заново.",
            reply_markup=back_to_delivery_kb().as_markup()
        )
        return

    kb = pvz_list_kb(pvz_list)
    kb.button(text="↩", callback_data="order:back")
    await message.answer(
        "Выберите пункт выдачи:",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(OrderStates.entering_pvz_or_address)


@router.callback_query(F.data.startswith("pvz:"))
async def on_pvz_choose(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохраняет выбранный ПВЗ и переводит к вводу ФИО.
    """
    _, pvz_id = callback.data.split(":")
    
    data = await state.get_data()
    if not data or not data.get("city"):
        await callback.answer("Сессия устарела, начните заново", show_alert=True)
        return

    await state.update_data(pvz_id=pvz_id, address=None)
    await callback.message.delete()
    await callback.message.answer(
        "Пожалуйста, введите ваши ФИО (Фамилия Имя Отчество):"
    )
    await state.set_state(OrderStates.entering_full_name)
    await callback.answer()


@router.message(OrderStates.entering_full_name, F.text.len() > 0)
async def on_full_name(message: Message, state: FSMContext) -> None:
    """
    Принимает ФИО и переходит к подтверждению (телефон берется из профиля пользователя).
    """
    full_name = message.text.strip()
    if not validate_full_name(full_name):
        await message.answer("ФИО некорректно. Укажите полностью, минимум 3 символа.", reply_markup=back_to_delivery_kb().as_markup())
        return
    
    # Получаем телефон пользователя из профиля
    try:
        async with repo.get_session() as session:
            user = await repo._resolve_user(session, message.from_user.id)
            if not user or not user.phone:
                await message.answer(
                    "Ошибка: телефон не найден в профиле. Пожалуйста, обновите профиль.",
                    reply_markup=back_to_delivery_kb().as_markup()
                )
                return
            phone = user.phone
    except Exception as e:
        await message.answer(
            f"Ошибка при получении данных: {escape(str(e))}",
            reply_markup=back_to_delivery_kb().as_markup()
        )
        return

    await state.update_data(full_name=full_name, phone=phone)
    data = await state.get_data()

    product_id = _extract_product_id(data)
    if product_id is None:
        await state.clear()
        await message.answer("Сессия устарела, начните оформление заново.")
        return

    product = await load_product_summary(product_id)
    if not product:
        await state.clear()
        await message.answer("Товар недоступен или уже куплен.")
        return

    summary = [
        f"Товар: {escape(str(product['title']))}",
        f"Категория: {escape(str(product['category'] or '—'))}",
        f"Стоимость: {escape(str(product['price']))} баллов",
        f"Город: {escape(str(data.get('city') or ''))}",
        f"Получатель: {escape(str(data.get('full_name') or ''))}",
        f"Телефон: {escape(str(phone or ''))}",
    ]

    await state.set_state(OrderStates.confirming)
    await message.answer(
        "Проверьте данные:\n\n" + "\n".join(summary),
        reply_markup=confirm_kb().as_markup(),
    )


@router.message(OrderStates.entering_phone, F.text.len() > 0)
async def on_phone(message: Message, state: FSMContext) -> None:
    """
    DEPRECATED: Этот обработчик больше не используется.
    Телефон теперь берется автоматически из профиля пользователя.
    """
    await message.answer("Этот этап пропущен. Телефон берется из вашего профиля.")
    # Это нужно для безопасности, чтобы не было ошибки 404 если кто-то вдруг попадет в это состояние


@router.callback_query(F.data == "order:cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменяет оформление заказа и сбрасывает состояние.
    """
    await state.clear()
    await callback.message.edit_text(
        "Оформление заказа отменено.",
        reply_markup=back_to_delivery_kb().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "order:confirm")
async def on_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Завершает сбор данных и создаёт заказ.
    """
    data = await state.get_data()
    if not data:
        await callback.answer("Сессия устарела, начните заново", show_alert=True)
        return

    try:
        product_id = int(data.get("product_id"))
        pvz_id = data.get("pvz_id")
    except Exception:
        await callback.message.edit_text("Сессия устарела, начните оформление заново.")
        await callback.answer()
        return

    if not pvz_id:
        await callback.message.edit_text("Не выбран пункт выдачи.")
        await callback.answer()
        return

    allowed, msg = await ensure_purchase_allowed(callback.from_user.id, product_id)
    if not allowed:
        await callback.message.edit_text(msg)
        await callback.answer()
        return

    user_id = callback.from_user.id

    try:
        info_dict = await finalize_successful_order(
            user_id=user_id,
            product_id=product_id,
            pvz_id=pvz_id,
            full_name=data.get("full_name", ""),
        )
    except ValueError as e:
        await callback.message.edit_text(escape(str(e)))
        await callback.answer()
        return

    text = format_order_message(info_dict, "pvz", "")

    await state.clear()
    # После успешного оформления показываем кнопку возврата в главное меню
    kb = InlineKeyboardBuilder()
    kb.button(text="↩", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(
        text,
        reply_markup=kb.as_markup(),
    )
    await callback.answer()
