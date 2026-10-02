from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class OrderCB(CallbackData, prefix="ord"):
    """
    CallbackData для пользовательских действий с заказами.

    Не содержит административные действия.
    Для админской части используется PaymentAdminCB
    и отдельные callback-классы административных разделов.
    """

    action: str
    order_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list      — список заказов пользователя
    # open      — открыть заказ
    # page      — переключить страницу
    # refresh   — обновить статус заказа
    # payment   — перейти к оплате
    # cancel    — отменить заказ
    # back      — назад
    # home      — вернуться в профиль


class OrderAdminCB(CallbackData, prefix="admo"):
    """CallbackData административных действий с заказами."""

    action: str
    order_id: int = 0
    page: int = 1


__all__ = [
    "OrderCB",
    "OrderAdminCB",
]