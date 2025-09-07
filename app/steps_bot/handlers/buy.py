from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import Any

from app.steps_bot.presentation.keyboards.cdek_kb import pvz_list_kb
from app.steps_bot.services.buy_service import (
    finalize_successful_order,
    format_order_message,
    load_product_summary,
    submit_order_to_cdek,
    ensure_purchase_allowed,
)
from app.steps_bot.services.cdek_client import cdek_client
from app.steps_bot.services.cdek_errors import CDEKAuthError, CDEKApiError
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


def delivery_type_kb() -> InlineKeyboardBuilder:
    """
    Возвращает клавиатуру выбора типа доставки.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="ПВЗ СДЭК", callback_data="order:delivery:pvz")
    kb.button(text="Курьер СДЭК", callback_data="order:delivery:courier")
    kb.adjust(2)
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


def delivery_type_kb(return_cb: str | None = None) -> InlineKeyboardBuilder:
    """
    Клавиатура выбора типа доставки: только ПВЗ + назад к товарам.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="ПВЗ СДЭК", callback_data="order:delivery:pvz")
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
    await callback.message.edit_text(
        "Выберите тип доставки:",
        reply_markup=delivery_type_kb(return_cb).as_markup(),
    )
    await callback.answer()


def _extract_product_id(data: dict[str, Any]) -> int | None:
    """
    Достаёт product_id из состояния и валидирует тип.
    Возвращает None, если идентификатор отсутствует.
    """
    value = data.get("product_id")
    return value if isinstance(value, int) else None

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
    Обрабатывает ввод города, предлагает ПВЗ или запрашивает адрес.
    """
    city = message.text.strip()
    if not validate_city(city):
        await message.answer("Город указан некорректно. Повторите ввод.", reply_markup=back_to_delivery_kb().as_markup())
        return

    await state.update_data(city=city)
    data = await state.get_data()

    if data.get("delivery_type") == "pvz":
        try:
            city_code = await cdek_client.find_city_code(city)
        except CDEKAuthError:
            await message.answer("Не удалось авторизоваться в СДЭК. Проверь настройки интеграции.", reply_markup=back_to_delivery_kb().as_markup())
            return
        except CDEKApiError as e:
            await message.answer(f"Сервис СДЭК недоступен: {escape(str(e))}", reply_markup=back_to_delivery_kb().as_markup())
            return

        if not city_code:
            await message.answer("Город не найден в справочнике СДЭК. Уточните название.", reply_markup=back_to_delivery_kb().as_markup())
            return

        await state.update_data(city_code=city_code, pvz_page=0)

        try:
            items = await cdek_client.list_pvz(city_code=city_code, page=0, size=10)
        except CDEKAuthError:
            await message.answer("Не удалось авторизоваться в СДЭК. Проверь настройки интеграции.", reply_markup=back_to_delivery_kb().as_markup())
            return
        except CDEKApiError as e:
            await message.answer(f"Не удалось получить список ПВЗ: {escape(str(e))}", reply_markup=back_to_delivery_kb().as_markup())
            return

        if not items:
            await message.answer("В городе нет доступных ПВЗ. Выберите курьерскую доставку.", reply_markup=back_to_delivery_kb().as_markup())
            return

        kb = pvz_list_kb(items, page=0, city_code=city_code)
        kb.button(text="↩", callback_data="order:back")
        await message.answer(
            "Выберите пункт выдачи:",
            reply_markup=kb.as_markup(),
        )
        await state.set_state(OrderStates.entering_pvz_or_address)
    else:
        await state.set_state(OrderStates.entering_pvz_or_address)
        await message.answer(
            "Укажите адрес для курьерской доставки:",
            reply_markup=back_to_delivery_kb().as_markup(),
        )


@router.callback_query(F.data.startswith("pvz_page:"))
async def on_pvz_page(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает пагинацию списка ПВЗ вне зависимости от состояния.
    """
    try:
        _, city_code, page = callback.data.split(":")
        city_code_i = int(city_code)
        page_i = max(int(page), 0)
    except Exception:
        await callback.answer("Некорректная пагинация", show_alert=True)
        return

    try:
        items = await cdek_client.list_pvz(city_code=city_code_i, page=page_i, size=10)
    except CDEKAuthError:
        await callback.answer("Ошибка авторизации СДЭК", show_alert=True)
        return
    except CDEKApiError as e:
        await callback.answer(escape(str(e)), show_alert=True)
        return

    kb = pvz_list_kb(items, page=page_i, city_code=city_code_i)
    kb.button(text="↩", callback_data="order:back")

    await state.update_data(pvz_page=page_i, city_code=city_code_i)
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("pvz:"))
async def on_pvz_choose(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохраняет выбранный ПВЗ и переводит к вводу ФИО.
    """
    _, code = callback.data.split(":")
    if not validate_pvz_code(code):
        await callback.answer("Некорректный код ПВЗ", show_alert=True)
        return

    data = await state.get_data()
    if not data or not data.get("city"):
        await callback.answer("Сессия устарела, начните заново", show_alert=True)
        return

    await state.update_data(pvz_code=code, address=None)
    await state.set_state(OrderStates.entering_full_name)
    await callback.message.edit_text(
        "Укажите ФИО получателя полностью:",
        reply_markup=back_to_delivery_kb().as_markup(),
    )
    await callback.answer()


@router.message(OrderStates.entering_pvz_or_address, F.text.len() > 0)
async def on_address_for_courier(message: Message, state: FSMContext) -> None:
    """
    Принимает адрес для курьерской доставки и переходит к вводу ФИО.
    """
    data = await state.get_data()
    if data.get("delivery_type") != "courier":
        return
    text = message.text.strip()
    if not validate_address(text):
        await message.answer("Адрес слишком короткий. Укажите точнее.", reply_markup=back_to_delivery_kb().as_markup())
        return
    await state.update_data(address=text, pvz_code=None)
    await state.set_state(OrderStates.entering_full_name)
    await message.answer(
        "Укажите ФИО получателя полностью:",
        reply_markup=back_to_delivery_kb().as_markup(),
    )


@router.message(OrderStates.entering_full_name, F.text.len() > 0)
async def on_full_name(message: Message, state: FSMContext) -> None:
    """
    Принимает ФИО и запрашивает телефон.
    """
    full_name = message.text.strip()
    if not validate_full_name(full_name):
        await message.answer("ФИО некорректно. Укажите полностью, минимум 3 символа.", reply_markup=back_to_delivery_kb().as_markup())
        return
    await state.update_data(full_name=full_name)
    await state.set_state(OrderStates.entering_phone)
    await message.answer(
        "Укажите телефон в международном формате (например: +79991234567):",
        reply_markup=back_to_delivery_kb().as_markup(),
    )


@router.message(OrderStates.entering_phone, F.text.len() > 0)
async def on_phone(message: Message, state: FSMContext) -> None:
    """
    Принимает телефон, нормализует и предлагает подтверждение данных.
    """
    phone = normalize_phone(message.text)
    if not validate_phone(phone):
        await message.answer(
            "Телефон некорректен. Формат: +79991234567.",
            reply_markup=back_to_delivery_kb().as_markup(),
        )
        return

    await state.update_data(phone=phone)
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
        f"Тип доставки: {'ПВЗ' if data.get('delivery_type') == 'pvz' else 'Курьер'}",
        f"Город: {escape(str(data.get('city') or ''))}",
    ]
    if data.get("delivery_type") == "pvz":
        summary.append(f"Код ПВЗ: {escape(str(data.get('pvz_code') or ''))}")
    else:
        summary.append(f"Адрес: {escape(str(data.get('address') or ''))}")
    summary.extend(
        [
            f"Получатель: {escape(str(data.get('full_name') or ''))}",
            f"Телефон: {escape(str(data.get('phone') or ''))}",
        ]
    )

    await state.set_state(OrderStates.confirming)
    await message.answer(
        "Проверьте данные:\n\n" + "\n".join(summary),
        reply_markup=confirm_kb().as_markup(),
    )


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
    Отправляет заказ в СДЭК и завершает сбор данных, показывая кнопку возврата.
    """
    data = await state.get_data()
    if not data:
        await callback.answer("Сессия устарела, начните заново", show_alert=True)
        return

    try:
        product_id = int(data.get("product_id"))
    except Exception:
        await callback.message.edit_text("Сессия устарела, начните оформление заново.")
        await callback.answer()
        return

    allowed, msg = await ensure_purchase_allowed(callback.from_user.id, product_id)
    if not allowed:
        await callback.message.edit_text(msg)
        await callback.answer()
        return

    order = OrderInput(
        product_id=product_id,
        delivery_type=data["delivery_type"],
        city=data["city"],
        pvz_code=data.get("pvz_code"),
        address=data.get("address"),
        full_name=data["full_name"],
        phone=data["phone"],
    )
    city_code = data.get("city_code")
    user_id = callback.from_user.id

    try:
        created, info = await submit_order_to_cdek(order=order, user_id=user_id, city_code=city_code)
    except ValueError as e:
        await callback.message.edit_text(escape(str(e)))
        await callback.answer()
        return
    except CDEKAuthError:
        await callback.message.edit_text("Не удалось авторизоваться в СДЭК. Проверь настройки интеграции.")
        await callback.answer()
        return
    except CDEKApiError as e:
        await callback.message.edit_text(f"Сервис СДЭК недоступен: {escape(str(e))}")
        await callback.answer()
        return

    if not created:
        await callback.message.edit_text(f"Не удалось оформить заказ: {escape(str(info))}")
        await callback.answer()
        return

    try:
        info_dict = await finalize_successful_order(
            user_id=user_id,
            product_id=order.product_id,
            cdek_uuid=info,
        )
    except ValueError as e:
        await callback.message.edit_text(escape(str(e)))
        await callback.answer()
        return

    dest = data.get("pvz_code") if order.delivery_type == "pvz" else (data.get("address") or "")
    text = format_order_message(info_dict, order.delivery_type, dest)

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
