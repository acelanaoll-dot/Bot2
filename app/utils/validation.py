from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.config import settings


_USERNAME_RE = re.compile(
    r"^[A-Za-z0-9_]{1,32}$"
)

_SLUG_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)


def validate_text(
    value: str,
    *,
    field_name: str = "значение",
    min_length: int = 1,
    max_length: int | None = None,
) -> str:
    """
    Проверяет обычный текстовый ввод.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} должен быть строкой."
        )

    value = value.strip()

    if len(value) < min_length:
        raise ValueError(
            f"{field_name} слишком короткий."
        )

    limit = (
        max_length
        if max_length is not None
        else settings.security_max_text_length
    )

    if len(value) > limit:
        raise ValueError(
            f"{field_name} слишком длинный."
        )

    return value


def validate_username(
    username: str,
) -> str:
    """
    Проверяет Telegram username без @.
    """

    username = username.strip().lstrip("@")

    if not _USERNAME_RE.fullmatch(username):
        raise ValueError(
            "Некорректный Telegram username."
        )

    return username


def validate_slug(
    slug: str,
) -> str:
    """
    Проверяет slug.
    """

    slug = slug.strip().lower()

    if not _SLUG_RE.fullmatch(slug):
        raise ValueError(
            "Некорректный slug."
        )

    return slug


def validate_positive_decimal(
    value: str | Decimal,
    *,
    field_name: str = "сумма",
) -> Decimal:
    """
    Проверяет положительное число.
    """

    try:
        number = (
            value
            if isinstance(value, Decimal)
            else Decimal(str(value))
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            f"{field_name} должно быть числом."
        ) from exc

    if number <= 0:
        raise ValueError(
            f"{field_name} должно быть больше нуля."
        )

    return number


def validate_non_negative_decimal(
    value: str | Decimal,
    *,
    field_name: str = "сумма",
) -> Decimal:
    """
    Проверяет число >= 0.
    """

    try:
        number = (
            value
            if isinstance(value, Decimal)
            else Decimal(str(value))
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            f"{field_name} должно быть числом."
        ) from exc

    if number < 0:
        raise ValueError(
            f"{field_name} не может быть отрицательным."
        )

    return number


def validate_telegram_id(
    telegram_id: int,
) -> int:
    """
    Проверяет Telegram ID.
    """

    if not isinstance(telegram_id, int):
        raise ValueError(
            "Telegram ID должен быть целым числом."
        )

    if telegram_id <= 0:
        raise ValueError(
            "Некорректный Telegram ID."
        )

    return telegram_id


__all__ = [
    "validate_text",
    "validate_username",
    "validate_slug",
    "validate_positive_decimal",
    "validate_non_negative_decimal",
    "validate_telegram_id",
]