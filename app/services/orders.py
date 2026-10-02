# app/services/orders.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    BalanceTransactionType,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
)
from app.database.session import write_transaction
from app.services.balance import (
    BalanceError,
    InsufficientBalanceError,
    balance_service,
)


# ============================================================
# Константы
# ============================================================

MONEY_QUANT = Decimal("0.00000001")
ZERO = Decimal("0")


# ============================================================
# Исключения
# ============================================================


class OrderServiceError(Exception):
    """Базовая ошибка сервиса заказов."""


class OrderNotFoundError(OrderServiceError):
    """Заказ не найден."""


class CartEmptyError(OrderServiceError):
    """Корзина пользователя пуста."""


# Compatibility name used by older handlers.
EmptyCartError = CartEmptyError


class ProductNotFoundError(OrderServiceError):
    """Товар не найден."""


class ProductInactiveError(OrderServiceError):
    """Товар недоступен для покупки."""


class InsufficientStockError(OrderServiceError):
    """Недостаточно товара на складе."""


class InvalidOrderAmountError(OrderServiceError):
    """Некорректная сумма заказа."""


class OrderAlreadyPaidError(OrderServiceError):
    """Заказ уже полностью оплачен."""


class OrderCancelledError(OrderServiceError):
    """Заказ отменён и не может быть изменён."""


class OrderExpiredError(OrderServiceError):
    """Заказ просрочен."""


class InvalidOrderStateError(OrderServiceError):
    """Недопустимое состояние заказа."""


class PaymentAmountExceededError(OrderServiceError):
    """Попытка зачислить больше остатка заказа."""


class PaymentAlreadyAppliedError(OrderServiceError):
    """Платёж с таким ключом уже применён."""


# ============================================================
# Результаты
# ============================================================


@dataclass(slots=True)
class OrderTotals:
    """Расчёт итоговой суммы заказа."""

    subtotal_usd: Decimal
    discount_usd: Decimal
    total_usd: Decimal


@dataclass(slots=True)
class PaymentApplicationResult:
    """Результат применения платежа к заказу."""

    order_id: int
    payment_amount_usd: Decimal
    applied_amount_usd: Decimal
    remaining_amount_usd: Decimal
    is_fully_paid: bool
    already_applied: bool = False


@dataclass(slots=True)
class OrderCreateResult:
    """Результат создания заказа."""

    order: Order
    totals: OrderTotals


# ============================================================
# Вспомогательные функции
# ============================================================


def _utcnow() -> datetime:
    """Возвращает текущее время UTC."""

    return datetime.now(timezone.utc)


def _money(value: Decimal | int | float | str) -> Decimal:
    """Безопасно приводит значение к денежному Decimal."""

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvalidOrderAmountError(
            "Некорректное денежное значение."
        ) from exc

    if not result.is_finite():
        raise InvalidOrderAmountError(
            "Денежное значение должно быть конечным."
        )

    return result.quantize(MONEY_QUANT)


def _positive_money(value: Decimal | int | float | str) -> Decimal:
    """Проверяет положительную денежную сумму."""

    result = _money(value)

    if result <= ZERO:
        raise InvalidOrderAmountError(
            "Сумма должна быть больше нуля."
        )

    return result


def _order_number() -> str:
    """
    Генерирует человекочитаемый номер заказа.

    Формат:
    ORD-YYYYMMDD-XXXXXXXX
    """

    now = _utcnow()

    return (
        f"ORD-{now:%Y%m%d}-"
        f"{uuid4().hex[:8].upper()}"
    )


def _remaining(order: Order) -> Decimal:
    """Возвращает остаток суммы заказа."""

    total = _money(order.total_usd)
    paid = (
        _money(order.balance_paid_usd)
        + _money(order.crypto_paid_usd)
    )

    remaining = total - paid

    if remaining < ZERO:
        return ZERO

    return remaining


def _is_terminal_status(status: OrderStatus) -> bool:
    """Проверяет конечный статус заказа."""

    return status in {
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.REFUNDED,
    }


def _is_payable_status(status: OrderStatus) -> bool:
    """Проверяет возможность оплаты заказа."""

    return status == OrderStatus.PAYMENT_PENDING


# ============================================================
# OrderService
# ============================================================


class OrderService:
    """
    Сервис жизненного цикла заказа.

    Важные правила:

    1. Создание заказа выполняется атомарно.
    2. Склад уменьшается в той же транзакции.
    3. Повторный платёж с тем же idempotency key
       не должен повторно увеличивать оплату.
    4. Сумма оплаченного никогда не должна превышать total_usd.
    5. Баланс пользователя списывается через BalanceService.
    """

    # ========================================================
    # Расчёт
    # ========================================================

    @staticmethod
    def calculate_totals(
        items: list[CartItem],
        *,
        discount_usd: Decimal = ZERO,
    ) -> OrderTotals:
        """
        Рассчитывает subtotal / discount / total.

        Цена берётся непосредственно из текущего Product.price_usd.
        """

        if not items:
            raise CartEmptyError("Корзина пуста.")

        subtotal = ZERO

        for cart_item in items:
            product = cart_item.product

            if product is None:
                raise ProductNotFoundError(
                    f"Товар #{cart_item.product_id} не найден."
                )

            quantity = int(cart_item.quantity)

            if quantity <= 0:
                raise InvalidOrderAmountError(
                    f"Некорректное количество товара "
                    f"#{product.id}."
                )

            price = _money(product.price_usd)

            if price < ZERO:
                raise InvalidOrderAmountError(
                    f"Некорректная цена товара #{product.id}."
                )

            subtotal += price * quantity

        discount = _money(discount_usd)

        if discount < ZERO:
            raise InvalidOrderAmountError(
                "Скидка не может быть отрицательной."
            )

        if discount > subtotal:
            discount = subtotal

        total = subtotal - discount

        return OrderTotals(
            subtotal_usd=_money(subtotal),
            discount_usd=_money(discount),
            total_usd=_money(total),
        )

    # ========================================================
    # Создание заказа
    # ========================================================

    async def create_from_cart(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        discount_usd: Decimal = ZERO,
        promo_code_id: int | None = None,
        notes: str | None = None,
    ) -> OrderCreateResult:
        """
        Создаёт заказ из корзины пользователя.

        Все операции выполняются внутри одной транзакции:
        - блокировка/проверка товаров;
        - проверка остатков;
        - уменьшение stock;
        - создание Order;
        - создание OrderItem;
        - удаление корзины.
        """

        if user_id <= 0:
            raise ValueError("Некорректный user_id.")

        async with write_transaction(session):
            result = await session.execute(
                select(CartItem)
                .where(CartItem.user_id == user_id)
                .options(
                    selectinload(CartItem.product),
                )
                .order_by(CartItem.id.asc())
            )

            cart_items = list(result.scalars().all())

            if not cart_items:
                raise CartEmptyError(
                    "Корзина пользователя пуста."
                )

            # ------------------------------------------------
            # Проверяем товары ещё раз непосредственно перед
            # созданием заказа.
            # ------------------------------------------------

            product_ids = [
                item.product_id
                for item in cart_items
            ]

            products_result = await session.execute(
                select(Product)
                .where(Product.id.in_(product_ids))
                .order_by(Product.id.asc())
            )

            products = {
                product.id: product
                for product in products_result.scalars().all()
            }

            locked_items: list[tuple[CartItem, Product]] = []

            for cart_item in cart_items:
                product = products.get(
                    cart_item.product_id
                )

                if product is None:
                    raise ProductNotFoundError(
                        f"Товар #{cart_item.product_id} "
                        "больше не существует."
                    )

                if not product.is_active:
                    raise ProductInactiveError(
                        f"Товар «{product.name}» "
                        "больше недоступен."
                    )

                if product.is_hidden:
                    raise ProductInactiveError(
                        f"Товар «{product.name}» "
                        "скрыт и недоступен для покупки."
                    )

                if not product.allow_purchase:
                    raise ProductInactiveError(
                        f"Покупка товара «{product.name}» "
                        "отключена."
                    )

                quantity = int(cart_item.quantity)

                if quantity <= 0:
                    raise InvalidOrderAmountError(
                        f"Некорректное количество "
                        f"товара #{product.id}."
                    )

                if product.stock < quantity:
                    raise InsufficientStockError(
                        f"Недостаточно товара "
                        f"«{product.name}». "
                        f"Доступно: {product.stock}, "
                        f"нужно: {quantity}."
                    )

                locked_items.append(
                    (cart_item, product)
                )

            # ------------------------------------------------
            # Итоговая сумма.
            # ------------------------------------------------

            totals = self.calculate_totals(
                cart_items,
                discount_usd=discount_usd,
            )

            # ------------------------------------------------
            # Создаём заказ.
            # ------------------------------------------------

            order = Order(
                order_number=_order_number(),
                user_id=user_id,
                status=OrderStatus.PAYMENT_PENDING,
                subtotal_usd=totals.subtotal_usd,
                discount_usd=totals.discount_usd,
                total_usd=totals.total_usd,
                balance_paid_usd=ZERO,
                crypto_paid_usd=ZERO,
                promo_code_id=promo_code_id,
                payment_idempotency_key=None,
                notes=(
                    notes.strip()
                    if notes and notes.strip()
                    else None
                ),
                delivery_data=None,
                paid_at=None,
                delivered_at=None,
                cancelled_at=None,
            )

            session.add(order)

            await session.flush()

            # ------------------------------------------------
            # Уменьшаем склад и создаём OrderItem.
            # ------------------------------------------------

            for cart_item, product in locked_items:
                quantity = int(cart_item.quantity)

                # Дополнительная атомарная проверка.
                stock_update = await session.execute(
                    update(Product)
                    .where(
                        Product.id == product.id,
                        Product.stock >= quantity,
                        Product.is_active.is_(True),
                        Product.is_hidden.is_(False),
                        Product.allow_purchase.is_(True),
                    )
                    .values(
                        stock=Product.stock - quantity
                    )
                )

                if stock_update.rowcount != 1:
                    raise InsufficientStockError(
                        f"Не удалось зарезервировать "
                        f"товар «{product.name}»."
                    )

                unit_price = _money(
                    product.price_usd
                )

                item_total = _money(
                    unit_price * quantity
                )

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price_usd=unit_price,
                    total_price_usd=item_total,
                    delivery_data=None,
                )

                session.add(order_item)

            # ------------------------------------------------
            # Удаляем корзину только после успешного создания
            # всех OrderItem.
            # ------------------------------------------------

            await session.execute(
                delete(CartItem).where(
                    CartItem.user_id == user_id
                )
            )

            await session.flush()

            logger.info(
                "Создан заказ: order_id={}, "
                "order_number={}, user_id={}, total_usd={}",
                order.id,
                order.order_number,
                user_id,
                totals.total_usd,
            )

            return OrderCreateResult(
                order=order,
                totals=totals,
            )

    # ========================================================
    # Получение заказа
    # ========================================================

    async def get(
        self,
        session: AsyncSession,
        order_id: int,
        *,
        with_items: bool = True,
        with_payments: bool = True,
    ) -> Order | None:
        """Получает заказ по ID."""

        if order_id <= 0:
            return None

        query = select(Order).where(
            Order.id == order_id
        )

        options: list[Any] = []

        if with_items:
            options.append(
                selectinload(Order.items)
            )

        if with_payments:
            options.append(
                selectinload(Order.payments)
            )

        if options:
            query = query.options(*options)

        result = await session.execute(query)

        return result.scalar_one_or_none()

    async def get_or_raise(
        self,
        session: AsyncSession,
        order_id: int,
        *,
        with_items: bool = True,
        with_payments: bool = True,
    ) -> Order:
        """Получает заказ или выбрасывает OrderNotFoundError."""

        order = await self.get(
            session,
            order_id,
            with_items=with_items,
            with_payments=with_payments,
        )

        if order is None:
            raise OrderNotFoundError(
                f"Заказ #{order_id} не найден."
            )

        return order

    async def get_user_order(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        user_id: int,
    ) -> Order | None:
        """Получает заказ только принадлежащий пользователю."""

        if order_id <= 0 or user_id <= 0:
            return None

        result = await session.execute(
            select(Order)
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
            .options(
                selectinload(Order.items),
                selectinload(Order.payments),
            )
        )

        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Order]:
        """Возвращает список заказов пользователя."""

        if user_id <= 0:
            return []

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def list_user_orders(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        page: int = 1,
        per_page: int = 10,
    ) -> list[Order]:
        """Пагинация заказов пользователя."""

        page = max(1, page)
        per_page = max(1, min(per_page, 100))

        offset = (page - 1) * per_page

        return await self.get_user_orders(
            session,
            user_id=user_id,
            limit=per_page,
            offset=offset,
        )

    # ========================================================
    # Суммы
    # ========================================================

    async def get_remaining_amount(
        self,
        session: AsyncSession,
        *,
        order_id: int,
    ) -> Decimal:
        """Возвращает сумму, которую ещё нужно оплатить."""

        order = await self.get_or_raise(
            session,
            order_id,
            with_items=False,
            with_payments=False,
        )

        return _remaining(order)

    async def get_paid_amount(
        self,
        session: AsyncSession,
        *,
        order_id: int,
    ) -> Decimal:
        """Возвращает уже оплаченную сумму."""

        order = await self.get_or_raise(
            session,
            order_id,
            with_items=False,
            with_payments=False,
        )

        return _money(
            order.balance_paid_usd
            + order.crypto_paid_usd
        )

    # ========================================================
    # Оплата балансом
    # ========================================================

    async def add_balance_payment(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        user_id: int,
        amount_usd: Decimal,
        idempotency_key: str,
    ) -> PaymentApplicationResult:
        """
        Оплачивает заказ внутренним балансом.

        Сначала списывается баланс пользователя.
        Затем сумма фиксируется в Order.balance_paid_usd.

        Важно:
        BalanceService имеет собственную идемпотентность.
        """

        amount = _positive_money(amount_usd)

        if not idempotency_key:
            raise ValueError(
                "idempotency_key обязателен."
            )

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=False,
            )

            if order.user_id != user_id:
                raise OrderServiceError(
                    "Заказ принадлежит другому пользователю."
                )

            if order.status == OrderStatus.CANCELLED:
                raise OrderCancelledError(
                    "Заказ отменён."
                )

            if order.status == OrderStatus.EXPIRED:
                raise OrderExpiredError(
                    "Срок оплаты заказа истёк."
                )

            if order.status == OrderStatus.REFUNDED:
                raise InvalidOrderStateError(
                    "Заказ уже возвращён."
                )

            if order.status == OrderStatus.DELIVERED:
                raise OrderAlreadyPaidError(
                    "Заказ уже выдан."
                )

            remaining = _remaining(order)

            if remaining <= ZERO:
                raise OrderAlreadyPaidError(
                    "Заказ уже полностью оплачен."
                )

            if amount > remaining:
                raise PaymentAmountExceededError(
                    f"Остаток заказа: {remaining}, "
                    f"попытка списать: {amount}."
                )

            # ------------------------------------------------
            # Списываем баланс.
            #
            # BalanceService сам обрабатывает idempotency.
            # ------------------------------------------------

            try:
                balance_result = await balance_service.debit(
                    session,
                    user_id=user_id,
                    amount_usd=amount,
                    transaction_type=(
                        BalanceTransactionType.PURCHASE
                    ),
                    idempotency_key=idempotency_key,
                    order_id=order.id,
                    description=(
                        f"Оплата заказа "
                        f"{order.order_number}"
                    ),
                )
            except InsufficientBalanceError:
                raise
            except BalanceError:
                raise

            already_applied = bool(
                getattr(
                    balance_result,
                    "already_processed",
                    False,
                )
            )

            if not already_applied:
                order.balance_paid_usd = _money(
                    order.balance_paid_usd + amount
                )

            # Идемпотентность также фиксируем на уровне заказа.
            if order.payment_idempotency_key is None:
                order.payment_idempotency_key = (
                    idempotency_key
                )

            remaining_after = _remaining(order)

            if remaining_after <= ZERO:
                order.status = OrderStatus.PAID
                order.paid_at = _utcnow()

            await session.flush()

            return PaymentApplicationResult(
                order_id=order.id,
                payment_amount_usd=amount,
                applied_amount_usd=(
                    ZERO
                    if already_applied
                    else amount
                ),
                remaining_amount_usd=remaining_after,
                is_fully_paid=(
                    remaining_after <= ZERO
                ),
                already_applied=already_applied,
            )

    # ========================================================
    # Криптооплата
    # ========================================================

    async def add_crypto_payment(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        amount_usd: Decimal,
        idempotency_key: str,
    ) -> PaymentApplicationResult:
        """
        Фиксирует успешную криптооплату заказа.

        Здесь баланс пользователя НЕ списывается.

        idempotency_key должен быть связан с уникальным
        внешним платежом, например:

            cryptopay:invoice_id

        или:

            nowpayments:payment_id
        """

        amount = _positive_money(amount_usd)

        if not idempotency_key:
            raise ValueError(
                "idempotency_key обязателен."
            )

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=False,
            )

            if order.status == OrderStatus.CANCELLED:
                raise OrderCancelledError(
                    "Заказ отменён."
                )

            if order.status == OrderStatus.EXPIRED:
                raise OrderExpiredError(
                    "Срок оплаты заказа истёк."
                )

            if order.status == OrderStatus.REFUNDED:
                raise InvalidOrderStateError(
                    "Заказ возвращён."
                )

            if order.status == OrderStatus.DELIVERED:
                raise OrderAlreadyPaidError(
                    "Заказ уже выдан."
                )

            remaining = _remaining(order)

            if remaining <= ZERO:
                raise OrderAlreadyPaidError(
                    "Заказ уже полностью оплачен."
                )

            # ------------------------------------------------
            # Ищем уже применённую транзакцию по ключу.
            #
            # Это позволяет webhook + polling безопасно
            # обрабатывать один и тот же платёж несколько раз.
            # ------------------------------------------------

            duplicate_result = await session.execute(
                select(Order)
                .where(
                    Order.payment_idempotency_key
                    == idempotency_key,
                    Order.id == order.id,
                )
            )

            duplicate_order = (
                duplicate_result.scalar_one_or_none()
            )

            if duplicate_order is not None:
                return PaymentApplicationResult(
                    order_id=order.id,
                    payment_amount_usd=amount,
                    applied_amount_usd=ZERO,
                    remaining_amount_usd=_remaining(
                        order
                    ),
                    is_fully_paid=(
                        _remaining(order) <= ZERO
                    ),
                    already_applied=True,
                )

            # ------------------------------------------------
            # Сумма внешнего платежа не может превышать
            # остаток заказа.
            # ------------------------------------------------

            if amount > remaining:
                raise PaymentAmountExceededError(
                    f"Платёж {amount} превышает "
                    f"остаток заказа {remaining}."
                )

            # ------------------------------------------------
            # Сохраняем ключ применения.
            #
            # У Order.payment_idempotency_key стоит UNIQUE.
            # Это дополнительный уровень защиты от повторного
            # применения одного внешнего платежа.
            # ------------------------------------------------

            order.payment_idempotency_key = (
                idempotency_key
            )

            order.crypto_paid_usd = _money(
                order.crypto_paid_usd + amount
            )

            remaining_after = _remaining(order)

            if remaining_after <= ZERO:
                order.status = OrderStatus.PAID
                order.paid_at = _utcnow()

            try:
                await session.flush()
            except IntegrityError as exc:
                logger.warning(
                    "Повторное применение crypto payment: "
                    "order_id={}, idempotency_key={}",
                    order.id,
                    idempotency_key,
                )

                # Не оставляем сессию в ошибочном состоянии.
                await session.rollback()

                existing = await self.get(
                    session,
                    order.id,
                    with_items=False,
                    with_payments=False,
                )

                if existing is None:
                    raise OrderNotFoundError(
                        f"Заказ #{order.id} не найден."
                    ) from exc

                return PaymentApplicationResult(
                    order_id=existing.id,
                    payment_amount_usd=amount,
                    applied_amount_usd=ZERO,
                    remaining_amount_usd=_remaining(
                        existing
                    ),
                    is_fully_paid=(
                        _remaining(existing) <= ZERO
                    ),
                    already_applied=True,
                )

            return PaymentApplicationResult(
                order_id=order.id,
                payment_amount_usd=amount,
                applied_amount_usd=amount,
                remaining_amount_usd=remaining_after,
                is_fully_paid=(
                    remaining_after <= ZERO
                ),
                already_applied=False,
            )

    # ========================================================
    # Отмена
    # ========================================================

    async def cancel(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        reason: str | None = None,
    ) -> Order:
        """Отменяет заказ."""

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=False,
            )

            if order.status == OrderStatus.DELIVERED:
                raise InvalidOrderStateError(
                    "Выданный заказ нельзя отменить."
                )

            if order.status == OrderStatus.REFUNDED:
                raise InvalidOrderStateError(
                    "Возвращённый заказ нельзя отменить."
                )

            if order.status == OrderStatus.CANCELLED:
                return order

            order.status = OrderStatus.CANCELLED
            order.cancelled_at = _utcnow()

            if reason:
                reason = reason.strip()

                if reason:
                    order.notes = (
                        f"{order.notes}\n"
                        if order.notes
                        else ""
                    ) + f"Отмена: {reason}"

            await session.flush()

            logger.info(
                "Заказ отменён: order_id={}, reason={}",
                order.id,
                reason,
            )

            return order

    async def cancel_order(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        reason: str | None = None,
    ) -> Order:
        """Совместимый алиас cancel()."""

        return await self.cancel(
            session,
            order_id=order_id,
            reason=reason,
        )

    # ========================================================
    # Просрочка
    # ========================================================

    async def expire(
        self,
        session: AsyncSession,
        *,
        order_id: int,
    ) -> Order:
        """Переводит неоплаченный заказ в EXPIRED."""

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=False,
            )

            if order.status != OrderStatus.PAYMENT_PENDING:
                return order

            if _remaining(order) <= ZERO:
                order.status = OrderStatus.PAID
                order.paid_at = (
                    order.paid_at or _utcnow()
                )

                await session.flush()

                return order

            order.status = OrderStatus.EXPIRED
            order.cancelled_at = _utcnow()

            await session.flush()

            logger.info(
                "Заказ просрочен: order_id={}",
                order.id,
            )

            return order

    async def expire_order(
        self,
        session: AsyncSession,
        *,
        order_id: int,
    ) -> Order:
        """Совместимый алиас expire()."""

        return await self.expire(
            session,
            order_id=order_id,
        )

    # ========================================================
    # Выдача
    # ========================================================

    async def deliver(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        delivery_data: dict[str, Any] | None = None,
    ) -> Order:
        """
        Помечает полностью оплаченный заказ как DELIVERED.

        Фактическая отправка товара пользователю должна
        выполняться handler/service доставки отдельно.
        """

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=False,
            )

            if order.status == OrderStatus.DELIVERED:
                return order

            if order.status != OrderStatus.PAID:
                raise InvalidOrderStateError(
                    "Выдать можно только полностью "
                    "оплаченный заказ."
                )

            order.status = OrderStatus.DELIVERED
            order.delivered_at = _utcnow()

            if delivery_data is not None:
                order.delivery_data = delivery_data

            await session.flush()

            logger.info(
                "Заказ выдан: order_id={}",
                order.id,
            )

            return order

    async def deliver_order(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        delivery_data: dict[str, Any] | None = None,
    ) -> Order:
        """Совместимый алиас deliver()."""

        return await self.deliver(
            session,
            order_id=order_id,
            delivery_data=delivery_data,
        )

    # ========================================================
    # Возврат
    # ========================================================

    async def refund(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        reason: str | None = None,
        refund_balance: bool = True,
    ) -> Order:
        """
        Возвращает оплаченный заказ.

        Если refund_balance=True, сумма оплаченная
        внутренним балансом возвращается пользователю.

        Криптоплатёж автоматически наружу здесь НЕ отправляется.
        Для внешнего возврата криптовалюты нужен отдельный gateway
        workflow с подтверждением администратора.
        """

        async with write_transaction(session):
            order = await self.get_or_raise(
                session,
                order_id,
                with_items=False,
                with_payments=True,
            )

            if order.status == OrderStatus.REFUNDED:
                return order

            if order.status not in {
                OrderStatus.PAID,
                OrderStatus.DELIVERED,
            }:
                raise InvalidOrderStateError(
                    "Возврат доступен только для "
                    "оплаченного или выданного заказа."
                )

            balance_refund = _money(
                order.balance_paid_usd
            )

            if refund_balance and balance_refund > ZERO:
                refund_key = (
                    f"refund:order:{order.id}:"
                    f"balance:{order.id}"
                )

                try:
                    await balance_service.credit(
                        session,
                        user_id=order.user_id,
                        amount_usd=balance_refund,
                        transaction_type=(
                            BalanceTransactionType.REFUND
                        ),
                        idempotency_key=refund_key,
                        order_id=order.id,
                        description=(
                            f"Возврат за заказ "
                            f"{order.order_number}"
                        ),
                    )
                except BalanceError:
                    raise

            order.status = OrderStatus.REFUNDED

            if reason:
                reason = reason.strip()

                if reason:
                    order.notes = (
                        f"{order.notes}\n"
                        if order.notes
                        else ""
                    ) + f"Возврат: {reason}"

            await session.flush()

            logger.info(
                "Заказ возвращён: order_id={}, "
                "balance_refund_usd={}",
                order.id,
                balance_refund,
            )

            return order

    async def refund_order(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        reason: str | None = None,
        refund_balance: bool = True,
    ) -> Order:
        """Совместимый алиас refund()."""

        return await self.refund(
            session,
            order_id=order_id,
            reason=reason,
            refund_balance=refund_balance,
        )


# ============================================================
# Глобальный экземпляр
# ============================================================


order_service = OrderService()


__all__ = [
    "OrderService",
    "OrderServiceError",
    "OrderNotFoundError",
    "CartEmptyError",
    "EmptyCartError",
    "ProductNotFoundError",
    "ProductInactiveError",
    "InsufficientStockError",
    "InvalidOrderAmountError",
    "OrderAlreadyPaidError",
    "OrderCancelledError",
    "OrderExpiredError",
    "InvalidOrderStateError",
    "PaymentAmountExceededError",
    "PaymentAlreadyAppliedError",
    "OrderTotals",
    "PaymentApplicationResult",
    "OrderCreateResult",
    "order_service",
]