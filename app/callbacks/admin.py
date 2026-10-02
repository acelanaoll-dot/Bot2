from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class AdminCB(CallbackData, prefix="adm"):
    """
    Основной callback административной панели.

    Здесь только навигация верхнего уровня.
    Операции конкретных разделов должны использовать
    специализированные callback-классы ниже.
    """

    action: str
    page: int = 1

    # Возможные action:
    #
    # menu       — открыть админ-меню
    # stats      — статистика
    # products   — товары
    # categories — категории
    # orders     — заказы
    # users      — пользователи
    # finance    — финансы
    # broadcast  — рассылка
    # promo      — промокоды
    # settings   — настройки
    # topup      — настройки пополнений
    # gateways   — платёжные шлюзы
    # admins     — администраторы
    # backups    — резервные копии
    # logs       — логи
    # back       — назад


class AdminProductCB(CallbackData, prefix="admp"):
    """Административные действия с товарами."""

    action: str
    product_id: int = 0
    category_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список товаров
    # open          — открыть товар
    # create        — создать товар
    # edit          — редактировать товар
    # delete        — удалить товар
    # activate      — активировать
    # deactivate    — скрыть
    # stock         — изменить остаток
    # price         — изменить цену
    # photos        — управление фотографиями
    # media         — управление медиагруппой
    # back          — назад


class AdminCategoryCB(CallbackData, prefix="admc"):
    """Административные действия с категориями."""

    action: str
    category_id: int = 0
    parent_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список категорий
    # open          — открыть категорию
    # create        — создать категорию
    # edit          — редактировать
    # delete        — удалить
    # order         — изменить порядок
    # activate      — включить
    # deactivate    — скрыть
    # back          — назад


class AdminOrderCB(CallbackData, prefix="admo"):
    """Административные действия с заказами."""

    action: str
    order_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список заказов
    # open          — открыть заказ
    # filter        — фильтр
    # deliver       — ручная выдача
    # mark_paid     — отметить оплаченным
    # refund        — возврат
    # cancel        — отменить
    # refresh       — обновить
    # back          — назад


class AdminUserCB(CallbackData, prefix="admu"):
    """Административные действия с пользователями."""

    action: str
    user_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список пользователей
    # open          — открыть пользователя
    # search        — поиск
    # balance       — баланс
    # history       — история операций
    # ban           — заблокировать
    # unban         — разблокировать
    # back          — назад


class AdminFinanceCB(CallbackData, prefix="admf"):
    """Административные финансовые операции."""

    action: str
    user_id: int = 0
    payment_id: int = 0
    topup_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # overview      — финансовая сводка
    # transactions  — операции
    # payments      — платежи
    # topups        — пополнения
    # export        — экспорт CSV
    # sync          — синхронизация платежей
    # back          — назад


class AdminGatewayCB(CallbackData, prefix="admg"):
    """Административное управление платёжными шлюзами."""

    action: str
    gateway: str = ""
    page: int = 1

    # Возможные action:
    #
    # list          — список шлюзов
    # open          — открыть шлюз
    # enable        — включить
    # disable       — отключить
    # edit          — изменить настройки
    # test          — проверить соединение
    # sync          — ручная синхронизация
    # back          — назад


class AdminSettingsCB(CallbackData, prefix="adms"):
    """Административные настройки магазина."""

    action: str
    key: str = ""
    page: int = 1

    # Возможные action:
    #
    # list          — список настроек
    # open          — открыть настройку
    # edit          — изменить
    # reset         — сбросить
    # back          — назад


class AdminBackupCB(CallbackData, prefix="admb"):
    """Административное управление резервными копиями."""

    action: str
    backup_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список резервных копий
    # create        — создать копию
    # download      — скачать копию
    # delete        — удалить копию
    # back          — назад


class AdminBroadcastCB(CallbackData, prefix="admbc"):
    """CallbackData рассылок."""

    action: str
    broadcast_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список рассылок
    # create        — создать рассылку
    # open          — открыть рассылку
    # start         — запустить
    # cancel        — отменить
    # stats         — статистика
    # back          — назад


class AdminPromoCB(CallbackData, prefix="admpromo"):
    """Административные действия с промокодами."""

    action: str
    promo_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # list          — список промокодов
    # create        — создать
    # open          — открыть
    # edit          — редактировать
    # activate      — активировать
    # deactivate    — деактивировать
    # delete        — удалить
    # back          — назад


class AdminCBAction(CallbackData, prefix="adma"):
    """
    Универсальные подтверждения административных действий.

    Используется только там, где отдельный callback-класс
    не нужен. Основные сущности должны использовать
    специализированные классы выше.
    """

    action: str
    target_id: int = 0
    page: int = 1

    # Возможные action:
    #
    # confirm       — подтвердить действие
    # cancel        — отменить действие
    # back          — назад


# Compatibility aliases for older keyboard code.
# All administrative handlers currently consume the unified AdminCB schema.
AdminMenuCB = AdminCB
AdminStatsCB = AdminCB
AdminTopupCB = AdminCB
AdminLogCB = AdminCB
AdminTextCB = AdminCB


__all__ = [
    "AdminCB",
    "AdminMenuCB",
    "AdminStatsCB",
    "AdminTopupCB",
    "AdminLogCB",
    "AdminTextCB",
    "AdminProductCB",
    "AdminCategoryCB",
    "AdminOrderCB",
    "AdminUserCB",
    "AdminFinanceCB",
    "AdminGatewayCB",
    "AdminSettingsCB",
    "AdminBackupCB",
    "AdminBroadcastCB",
    "AdminPromoCB",
    "AdminCBAction",
]