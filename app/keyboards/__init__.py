from __future__ import annotations

from app.keyboards.admin import (
    admin_backup_keyboard,
    admin_broadcast_keyboard,
    admin_category_keyboard,
    admin_finance_keyboard,
    admin_gateway_keyboard,
    admin_menu_keyboard,
    admin_order_keyboard,
    admin_product_keyboard,
    admin_promo_keyboard,
    admin_settings_keyboard,
    admin_user_keyboard,
)
from app.keyboards.cart import cart_keyboard
from app.keyboards.catalog import (
    catalog_categories_keyboard,
    catalog_category_keyboard,
    catalog_product_keyboard,
)
from app.keyboards.checkout import (
    checkout_keyboard,
    payment_methods_keyboard,
)
from app.keyboards.payment import (
    admin_payment_keyboard,
    invoice_keyboard,
    payment_status_keyboard,
    topup_amount_keyboard,
    topup_asset_keyboard,
    topup_history_keyboard,
    topup_invoice_keyboard,
    topup_menu_keyboard,
    topup_payment_keyboard,
    topup_support_keyboard,
)
from app.keyboards.user import (
    balance_keyboard,
    language_keyboard,
    main_menu_keyboard,
    profile_keyboard,
    referral_keyboard,
    support_keyboard,
)


__all__ = [
    # Основное пользовательское меню
    "main_menu_keyboard",
    "profile_keyboard",
    "balance_keyboard",
    "referral_keyboard",
    "language_keyboard",
    "support_keyboard",

    # Каталог
    "catalog_categories_keyboard",
    "catalog_category_keyboard",
    "catalog_product_keyboard",

    # Корзина / оформление
    "cart_keyboard",
    "checkout_keyboard",
    "payment_methods_keyboard",

    # Платежи / пополнение
    "invoice_keyboard",
    "payment_status_keyboard",
    "topup_menu_keyboard",
    "topup_amount_keyboard",
    "topup_asset_keyboard",
    "topup_payment_keyboard",
    "topup_invoice_keyboard",
    "topup_history_keyboard",
    "topup_support_keyboard",

    # Админка
    "admin_menu_keyboard",
    "admin_product_keyboard",
    "admin_category_keyboard",
    "admin_order_keyboard",
    "admin_user_keyboard",
    "admin_finance_keyboard",
    "admin_broadcast_keyboard",
    "admin_promo_keyboard",
    "admin_settings_keyboard",
    "admin_backup_keyboard",
    "admin_gateway_keyboard",
    "admin_payment_keyboard",
]