from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks.admin import (
    AdminBackupCB,
    AdminBroadcastCB,
    AdminCategoryCB,
    AdminFinanceCB,
    AdminGatewayCB,
    AdminLogCB,
    AdminMenuCB,
    AdminOrderCB,
    AdminProductCB,
    AdminPromoCB,
    AdminSettingsCB,
    AdminStatsCB,
    AdminTextCB,
    AdminTopupCB,
    AdminUserCB,
)
from app.utils.i18n import t


def admin_main_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Главное меню администратора."""

    builder = InlineKeyboardBuilder()

    buttons = [
        (
            "admin.products",
            AdminMenuCB(action="products"),
        ),
        (
            "admin.categories",
            AdminMenuCB(action="categories"),
        ),
        (
            "admin.orders",
            AdminMenuCB(action="orders"),
        ),
        (
            "admin.users",
            AdminMenuCB(action="users"),
        ),
        (
            "admin.stats",
            AdminMenuCB(action="stats"),
        ),
        (
            "admin.finance",
            AdminMenuCB(action="finance"),
        ),
        (
            "admin.broadcast",
            AdminMenuCB(action="broadcast"),
        ),
        (
            "admin.promo",
            AdminMenuCB(action="promo"),
        ),
        (
            "admin.settings",
            AdminMenuCB(action="settings"),
        ),
        (
            "admin.topup",
            AdminMenuCB(action="topup"),
        ),
        (
            "admin.gateways",
            AdminMenuCB(action="gateways"),
        ),
        (
            "admin.admins",
            AdminMenuCB(action="admins"),
        ),
        (
            "admin.backups",
            AdminMenuCB(action="backups"),
        ),
        (
            "admin.logs",
            AdminMenuCB(action="logs"),
        ),
        (
            "admin.texts",
            AdminMenuCB(action="texts"),
        ),
    ]

    for translation_key, callback in buttons:
        builder.button(
            text=t(translation_key, language),
            callback_data=callback.pack(),
        )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="back",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_back_keyboard(
    *,
    language: str = "ru",
    action: str = "back",
) -> InlineKeyboardMarkup:
    """Универсальная кнопка возврата в админ-меню."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action=action,
        ).pack(),
    )

    return builder.as_markup()


def admin_product_keyboard(
    *,
    product_id: int = 0,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Управление товаром."""

    builder = InlineKeyboardBuilder()

    if product_id:
        builder.button(
            text=t("admin.product.edit", language),
            callback_data=AdminProductCB(
                action="edit",
                product_id=product_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.product.photo", language),
            callback_data=AdminProductCB(
                action="photos",
                product_id=product_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.product.stock", language),
            callback_data=AdminProductCB(
                action="stock",
                product_id=product_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.product.price", language),
            callback_data=AdminProductCB(
                action="price",
                product_id=product_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.product.toggle", language),
            callback_data=AdminProductCB(
                action="toggle",
                product_id=product_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.product.delete", language),
            callback_data=AdminProductCB(
                action="delete",
                product_id=product_id,
                page=page,
            ).pack(),
        )

    builder.button(
        text=t("admin.product.create", language),
        callback_data=AdminProductCB(
            action="create",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="products",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_product_list_keyboard(
    *,
    products: list[object],
    page: int,
    has_next: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Список товаров администратора."""

    builder = InlineKeyboardBuilder()

    for product in products:
        product_id = int(getattr(product, "id"))
        name = str(getattr(product, "name"))

        builder.button(
            text=name,
            callback_data=AdminProductCB(
                action="open",
                product_id=product_id,
                page=page,
            ).pack(),
        )

    if products:
        builder.adjust(1)

    if page > 0:
        builder.button(
            text=t("pagination.previous", language),
            callback_data=AdminProductCB(
                action="page",
                page=page - 1,
            ).pack(),
        )

    if has_next:
        builder.button(
            text=t("pagination.next", language),
            callback_data=AdminProductCB(
                action="page",
                page=page + 1,
            ).pack(),
        )

    builder.button(
        text=t("admin.product.create", language),
        callback_data=AdminProductCB(
            action="create",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="products",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_category_keyboard(
    *,
    category_id: int = 0,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Управление категорией."""

    builder = InlineKeyboardBuilder()

    if category_id:
        builder.button(
            text=t("admin.category.edit", language),
            callback_data=AdminCategoryCB(
                action="edit",
                category_id=category_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.category.order", language),
            callback_data=AdminCategoryCB(
                action="order",
                category_id=category_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.category.toggle", language),
            callback_data=AdminCategoryCB(
                action="toggle",
                category_id=category_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.category.delete", language),
            callback_data=AdminCategoryCB(
                action="delete",
                category_id=category_id,
                page=page,
            ).pack(),
        )

    builder.button(
        text=t("admin.category.create", language),
        callback_data=AdminCategoryCB(
            action="create",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="categories",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_category_list_keyboard(
    *,
    categories: list[object],
    page: int,
    has_next: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Список категорий администратора."""

    builder = InlineKeyboardBuilder()

    for category in categories:
        category_id = int(getattr(category, "id"))
        name = str(getattr(category, "name"))

        builder.button(
            text=name,
            callback_data=AdminCategoryCB(
                action="open",
                category_id=category_id,
                page=page,
            ).pack(),
        )

    if categories:
        builder.adjust(1)

    if page > 0:
        builder.button(
            text=t("pagination.previous", language),
            callback_data=AdminCategoryCB(
                action="page",
                page=page - 1,
            ).pack(),
        )

    if has_next:
        builder.button(
            text=t("pagination.next", language),
            callback_data=AdminCategoryCB(
                action="page",
                page=page + 1,
            ).pack(),
        )

    builder.button(
        text=t("admin.category.create", language),
        callback_data=AdminCategoryCB(
            action="create",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="categories",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_order_keyboard(
    *,
    order_id: int = 0,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Управление заказом."""

    builder = InlineKeyboardBuilder()

    if order_id:
        builder.button(
            text=t("admin.order.open", language),
            callback_data=AdminOrderCB(
                action="open",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.status", language),
            callback_data=AdminOrderCB(
                action="status",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.deliver", language),
            callback_data=AdminOrderCB(
                action="deliver",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.refund", language),
            callback_data=AdminOrderCB(
                action="refund",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.cancel", language),
            callback_data=AdminOrderCB(
                action="cancel",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.expire", language),
            callback_data=AdminOrderCB(
                action="expire",
                order_id=order_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.order.sync", language),
            callback_data=AdminOrderCB(
                action="sync",
                order_id=order_id,
                page=page,
            ).pack(),
        )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="orders",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_order_list_keyboard(
    *,
    orders: list[object],
    page: int,
    has_next: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Список заказов администратора."""

    builder = InlineKeyboardBuilder()

    for order in orders:
        order_id = int(getattr(order, "id"))
        order_number = str(
            getattr(order, "order_number", order_id)
        )

        builder.button(
            text=f"#{order_number}",
            callback_data=AdminOrderCB(
                action="open",
                order_id=order_id,
                page=page,
            ).pack(),
        )

    if orders:
        builder.adjust(1)

    if page > 0:
        builder.button(
            text=t("pagination.previous", language),
            callback_data=AdminOrderCB(
                action="page",
                page=page - 1,
            ).pack(),
        )

    if has_next:
        builder.button(
            text=t("pagination.next", language),
            callback_data=AdminOrderCB(
                action="page",
                page=page + 1,
            ).pack(),
        )

    builder.button(
        text=t("admin.order.filter", language),
        callback_data=AdminOrderCB(
            action="filter",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="orders",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_user_keyboard(
    *,
    user_id: int = 0,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Управление пользователем."""

    builder = InlineKeyboardBuilder()

    if user_id:
        builder.button(
            text=t("admin.user.open", language),
            callback_data=AdminUserCB(
                action="open",
                user_id=user_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.user.balance", language),
            callback_data=AdminUserCB(
                action="balance",
                user_id=user_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.user.history", language),
            callback_data=AdminUserCB(
                action="history",
                user_id=user_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.user.ban", language),
            callback_data=AdminUserCB(
                action="ban",
                user_id=user_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.user.unban", language),
            callback_data=AdminUserCB(
                action="unban",
                user_id=user_id,
                page=page,
            ).pack(),
        )

    builder.button(
        text=t("admin.user.search", language),
        callback_data=AdminUserCB(
            action="search",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="users",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_stats_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Статистика."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.stats.refresh", language),
        callback_data=AdminStatsCB(
            action="refresh",
        ).pack(),
    )

    builder.button(
        text=t("admin.stats.export", language),
        callback_data=AdminStatsCB(
            action="export",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="stats",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_finance_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Финансовый раздел."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.finance.summary", language),
        callback_data=AdminFinanceCB(
            action="summary",
        ).pack(),
    )

    builder.button(
        text=t("admin.finance.export", language),
        callback_data=AdminFinanceCB(
            action="export",
        ).pack(),
    )

    builder.button(
        text=t("admin.finance.transactions", language),
        callback_data=AdminFinanceCB(
            action="transactions",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="finance",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_broadcast_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Рассылки."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.broadcast.create", language),
        callback_data=AdminBroadcastCB(
            action="create",
        ).pack(),
    )

    builder.button(
        text=t("admin.broadcast.list", language),
        callback_data=AdminBroadcastCB(
            action="list",
        ).pack(),
    )

    builder.button(
        text=t("admin.broadcast.cancel", language),
        callback_data=AdminBroadcastCB(
            action="cancel",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="broadcast",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_promo_keyboard(
    *,
    promo_id: int = 0,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Промокоды."""

    builder = InlineKeyboardBuilder()

    if promo_id:
        builder.button(
            text=t("admin.promo.open", language),
            callback_data=AdminPromoCB(
                action="open",
                promo_id=promo_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.promo.edit", language),
            callback_data=AdminPromoCB(
                action="edit",
                promo_id=promo_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.promo.toggle", language),
            callback_data=AdminPromoCB(
                action="toggle",
                promo_id=promo_id,
                page=page,
            ).pack(),
        )

        builder.button(
            text=t("admin.promo.delete", language),
            callback_data=AdminPromoCB(
                action="delete",
                promo_id=promo_id,
                page=page,
            ).pack(),
        )

    builder.button(
        text=t("admin.promo.create", language),
        callback_data=AdminPromoCB(
            action="create",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="promo",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_topup_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Настройки пополнения и P2P-инструкции."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.topup.settings", language),
        callback_data=AdminTopupCB(
            action="settings",
        ).pack(),
    )

    builder.button(
        text=t("admin.topup.guide", language),
        callback_data=AdminTopupCB(
            action="guide",
        ).pack(),
    )

    builder.button(
        text=t("admin.topup.add_guide", language),
        callback_data=AdminTopupCB(
            action="add_guide",
        ).pack(),
    )

    builder.button(
        text=t("admin.topup.history", language),
        callback_data=AdminTopupCB(
            action="history",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="topup",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_gateway_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Платёжные шлюзы."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.gateway.cryptopay", language),
        callback_data=AdminGatewayCB(
            action="cryptopay",
        ).pack(),
    )

    builder.button(
        text=t("admin.gateway.nowpayments", language),
        callback_data=AdminGatewayCB(
            action="nowpayments",
        ).pack(),
    )

    builder.button(
        text=t("admin.gateway.priority", language),
        callback_data=AdminGatewayCB(
            action="priority",
        ).pack(),
    )

    builder.button(
        text=t("admin.gateway.sync", language),
        callback_data=AdminGatewayCB(
            action="sync",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="gateways",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_settings_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Общие настройки магазина."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.settings.shop", language),
        callback_data=AdminSettingsCB(
            action="shop",
        ).pack(),
    )

    builder.button(
        text=t("admin.settings.security", language),
        callback_data=AdminSettingsCB(
            action="security",
        ).pack(),
    )

    builder.button(
        text=t("admin.settings.subscription", language),
        callback_data=AdminSettingsCB(
            action="subscription",
        ).pack(),
    )

    builder.button(
        text=t("admin.settings.referrals", language),
        callback_data=AdminSettingsCB(
            action="referrals",
        ).pack(),
    )

    builder.button(
        text=t("admin.settings.backup", language),
        callback_data=AdminSettingsCB(
            action="backup",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="settings",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_backup_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Резервные копии."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.backup.create", language),
        callback_data=AdminBackupCB(
            action="create",
        ).pack(),
    )

    builder.button(
        text=t("admin.backup.list", language),
        callback_data=AdminBackupCB(
            action="list",
        ).pack(),
    )

    builder.button(
        text=t("admin.backup.download", language),
        callback_data=AdminBackupCB(
            action="download",
        ).pack(),
    )

    builder.button(
        text=t("admin.backup.cleanup", language),
        callback_data=AdminBackupCB(
            action="cleanup",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="back",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_log_keyboard(
    *,
    page: int = 0,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Просмотр административных логов."""

    builder = InlineKeyboardBuilder()

    if page > 0:
        builder.button(
            text=t("pagination.previous", language),
            callback_data=AdminLogCB(
                action="page",
                page=page - 1,
            ).pack(),
        )

    builder.button(
        text=t("admin.logs.refresh", language),
        callback_data=AdminLogCB(
            action="refresh",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("admin.logs.export", language),
        callback_data=AdminLogCB(
            action="export",
            page=page,
        ).pack(),
    )

    builder.button(
        text=t("pagination.next", language),
        callback_data=AdminLogCB(
            action="page",
            page=page + 1,
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="logs",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


def admin_text_keyboard(
    *,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Редактирование переводов."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text=t("admin.text.list", language),
        callback_data=AdminTextCB(
            action="list",
        ).pack(),
    )

    builder.button(
        text=t("admin.text.edit", language),
        callback_data=AdminTextCB(
            action="edit",
        ).pack(),
    )

    builder.button(
        text=t("admin.text.reset", language),
        callback_data=AdminTextCB(
            action="reset",
        ).pack(),
    )

    builder.button(
        text=t("common.back", language),
        callback_data=AdminMenuCB(
            action="texts",
        ).pack(),
    )

    builder.adjust(2)

    return builder.as_markup()


# Compatibility aliases used by administrative handlers.
admin_menu_keyboard = admin_main_keyboard
admin_products_keyboard = admin_product_list_keyboard
admin_categories_keyboard = admin_category_list_keyboard


__all__ = [
    "admin_main_keyboard",
    "admin_menu_keyboard",
    "admin_back_keyboard",
    "admin_product_keyboard",
    "admin_product_list_keyboard",
    "admin_products_keyboard",
    "admin_category_keyboard",
    "admin_category_list_keyboard",
    "admin_categories_keyboard",
    "admin_order_keyboard",
    "admin_order_list_keyboard",
    "admin_user_keyboard",
    "admin_stats_keyboard",
    "admin_finance_keyboard",
    "admin_broadcast_keyboard",
    "admin_promo_keyboard",
    "admin_topup_keyboard",
    "admin_gateway_keyboard",
    "admin_settings_keyboard",
    "admin_backup_keyboard",
    "admin_log_keyboard",
    "admin_text_keyboard",
]