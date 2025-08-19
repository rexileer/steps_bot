import re


def normalize_phone(value: str) -> str:
    """Нормализует телефон к формату +7XXXXXXXXXX или +XXXXXXXXXXX."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7") and len(digits) in (11, 12):
        digits = digits
    return f"+{digits}" if not digits.startswith("+") else digits


def validate_phone(value: str) -> bool:
    """Проверяет корректность телефона по простому правилу E.164."""
    phone = value.strip()
    return bool(re.fullmatch(r"\+\d{10,15}", phone))


def validate_full_name(value: str) -> bool:
    """Проверяет ФИО на минимальную длину и допустимые символы."""
    text = value.strip()
    if len(text) < 3:
        return False
    return bool(re.fullmatch(r"[A-Za-zА-Яа-яЁё\-\s]{3,}", text))


def validate_city(value: str) -> bool:
    """Базовая проверка города на непустое значение."""
    return bool(value and value.strip())


def validate_pvz_code(value: str) -> bool:
    """Базовая проверка кода ПВЗ на формат буквенно-цифровой строки."""
    return bool(re.fullmatch(r"[A-Za-z0-9\-\_]{3,}", value.strip()))


def validate_address(value: str) -> bool:
    """Базовая проверка адреса на минимальную длину."""
    return bool(value and len(value.strip()) >= 5)
