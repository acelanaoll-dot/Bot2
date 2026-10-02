from __future__ import annotations

"""Административные handlers и единый router админ-панели."""

from aiogram import Router

from app.handlers.admin.admins import router as admins_router
from app.handlers.admin.backups import router as backups_router
from app.handlers.admin.broadcast import router as broadcast_router
from app.handlers.admin.categories import router as categories_router
from app.handlers.admin.finance import router as finance_router
from app.handlers.admin.gateways import router as gateways_router
from app.handlers.admin.logs import router as logs_router
from app.handlers.admin.menu import router as menu_router
from app.handlers.admin.orders import router as orders_router
from app.handlers.admin.products import router as products_router
from app.handlers.admin.promo import router as promo_router
from app.handlers.admin.settings import router as settings_router
from app.handlers.admin.stats import router as stats_router
from app.handlers.admin.topup_settings import router as topup_settings_router
from app.handlers.admin.users import router as users_router


admin_router = Router(name="admin")

for _router in (
    menu_router,
    admins_router,
    backups_router,
    broadcast_router,
    categories_router,
    finance_router,
    gateways_router,
    logs_router,
    orders_router,
    products_router,
    promo_router,
    settings_router,
    stats_router,
    topup_settings_router,
    users_router,
):
    admin_router.include_router(_router)


__all__ = [
    "admin_router",
]
