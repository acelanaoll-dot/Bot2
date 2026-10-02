from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    BalanceTransaction,
    BalanceTransactionType,
    User,
)


class BalanceError(Exception):
    """Базовая ошибка операций с балансом."""


class InsufficientBalanceError(BalanceError):
    """Недостаточно средств."""


class InvalidBalanceAmountError(BalanceError):
    """Некорректная сумма."""


class BalanceIdempotencyConflictError(BalanceError):
    """Операция с таким ключом уже существует."""


@dataclass(slots=True)
class BalanceOperationResult:
    """Результат финансовой операции."""

    user_id: int
    old_balance: Decimal
    new_balance: Decimal
    amount: Decimal
    transaction: BalanceTransaction
    already_processed: bool = False


class BalanceService:
    """Безопасная работа с внутренним балансом."""

    @staticmethod
    def _validate_amount(
        amount_usd: Decimal,
    ) -> Decimal:
        """Проверить и округлить сумму."""
        try:
            amount = Decimal(str(amount_usd))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidBalanceAmountError(
                "Некорректная сумма операции."
            ) from exc

        if amount <= Decimal("0"):
            raise InvalidBalanceAmountError(
                "Сумма должна быть больше нуля."
            )

        return amount.quantize(Decimal("0.01"))

    @staticmethod
    async def _get_user(
        session: AsyncSession,
        user_id: int,
    ) -> User:
        """Получить пользователя."""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise BalanceError(
                f"Пользователь #{user_id} не найден."
            )

        return user

    @staticmethod
    async def _find_idempotent(
        session: AsyncSession,
        *,
        user_id: int,
        transaction_type: BalanceTransactionType,
        idempotency_key: str | None,
    ) -> BalanceTransaction | None:
        """Найти уже выполненную операцию."""
        if not idempotency_key:
            return None

        result = await session.execute(
            select(BalanceTransaction)
            .where(
                BalanceTransaction.user_id == user_id,
                BalanceTransaction.type == transaction_type,
                BalanceTransaction.idempotency_key
                == idempotency_key,
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    @staticmethod
    def _get_before_balance(
        *,
        current_balance: Decimal,
        amount: Decimal,
        is_debit: bool,
    ) -> Decimal:
        """Восстановить баланс до уже выполненной операции."""
        if is_debit:
            return current_balance + amount

        return current_balance - amount

    async def _change_balance(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        transaction_type: BalanceTransactionType,
        description: str,
        idempotency_key: str | None,
        order_id: int | None,
        topup_id: int | None,
        source_type: str | None,
        source_id: int | None,
        metadata: dict[str, Any] | None,
        is_debit: bool,
    ) -> BalanceOperationResult:
        """Изменить баланс внутри уже открытой транзакции."""

        amount = self._validate_amount(amount_usd)

        # ----------------------------------------------------------
        # Idempotency
        # ----------------------------------------------------------

        existing = await self._find_idempotent(
            session,
            user_id=user_id,
            transaction_type=transaction_type,
            idempotency_key=idempotency_key,
        )

        if existing is not None:
            user = await self._get_user(
                session,
                user_id,
            )

            current_balance = Decimal(
                str(user.balance_usd)
            )

            existing_amount = abs(
                Decimal(str(existing.amount_usd))
            )

            old_balance = self._get_before_balance(
                current_balance=current_balance,
                amount=existing_amount,
                is_debit=is_debit,
            )

            return BalanceOperationResult(
                user_id=user_id,
                old_balance=old_balance,
                new_balance=current_balance,
                amount=existing_amount,
                transaction=existing,
                already_processed=True,
            )

        # ----------------------------------------------------------
        # Получаем текущий баланс
        # ----------------------------------------------------------

        user = await self._get_user(
            session,
            user_id,
        )

        old_balance = Decimal(
            str(user.balance_usd)
        )

        # ----------------------------------------------------------
        # Списание
        # ----------------------------------------------------------

        if is_debit:
            new_balance = old_balance - amount

            if new_balance < Decimal("0"):
                raise InsufficientBalanceError(
                    f"Недостаточно средств. "
                    f"Баланс: {old_balance:.2f} USD, "
                    f"требуется: {amount:.2f} USD."
                )

            result = await session.execute(
                update(User)
                .where(
                    User.id == user_id,
                    User.balance_usd >= amount,
                )
                .values(
                    balance_usd=User.balance_usd - amount,
                )
            )

            if result.rowcount != 1:
                raise InsufficientBalanceError(
                    "Баланс изменился параллельно. "
                    "Операция списания отменена."
                )

            transaction_amount = -amount

        # ----------------------------------------------------------
        # Зачисление
        # ----------------------------------------------------------

        else:
            new_balance = old_balance + amount

            result = await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    balance_usd=User.balance_usd + amount,
                )
            )

            if result.rowcount != 1:
                raise BalanceError(
                    "Не удалось обновить баланс пользователя."
                )

            transaction_amount = amount

        # ----------------------------------------------------------
        # История операции
        # ----------------------------------------------------------

        transaction = BalanceTransaction(
            user_id=user_id,
            type=transaction_type,
            amount_usd=transaction_amount,
            balance_before_usd=old_balance,
            balance_after_usd=new_balance,
            idempotency_key=idempotency_key,
            order_id=order_id,
            topup_id=topup_id,
            source_type=source_type,
            source_id=source_id,
            description=description,
            metadata_json=metadata,
        )

        session.add(transaction)

        try:
            await session.flush()

        except IntegrityError as exc:
            # Важно: здесь НЕ считаем любой IntegrityError
            # успешной операцией.
            #
            # Если уникальность idempotency_key нарушена,
            # вызывающий код должен повторно прочитать операцию.
            if idempotency_key:
                raise BalanceIdempotencyConflictError(
                    "Операция с таким idempotency_key "
                    "уже существует."
                ) from exc

            raise

        logger.info(
            "Изменение баланса: user_id={}, "
            "type={}, amount={}, before={}, after={}, "
            "idempotency_key={}",
            user_id,
            transaction_type.value,
            transaction_amount,
            old_balance,
            new_balance,
            idempotency_key,
        )

        return BalanceOperationResult(
            user_id=user_id,
            old_balance=old_balance,
            new_balance=new_balance,
            amount=amount,
            transaction=transaction,
            already_processed=False,
        )

    async def credit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        transaction_type: BalanceTransactionType,
        description: str,
        idempotency_key: str | None = None,
        order_id: int | None = None,
        topup_id: int | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Зачислить деньги в текущей транзакции."""

        return await self._change_balance(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=transaction_type,
            description=description,
            idempotency_key=idempotency_key,
            order_id=order_id,
            topup_id=topup_id,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
            is_debit=False,
        )

    async def debit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        transaction_type: BalanceTransactionType,
        description: str,
        idempotency_key: str | None = None,
        order_id: int | None = None,
        topup_id: int | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Списать деньги в текущей транзакции."""

        return await self._change_balance(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=transaction_type,
            description=description,
            idempotency_key=idempotency_key,
            order_id=order_id,
            topup_id=topup_id,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
            is_debit=True,
        )

    async def refund(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        order_id: int | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Вернуть деньги пользователю."""

        return await self.credit(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=BalanceTransactionType.REFUND,
            description=description,
            idempotency_key=idempotency_key,
            order_id=order_id,
            source_type="refund",
            source_id=source_id,
            metadata=metadata,
        )

    async def referral_credit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Начислить реферальное вознаграждение."""

        return await self.credit(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=BalanceTransactionType.REFERRAL,
            description=description,
            idempotency_key=idempotency_key,
            source_type="referral",
            source_id=source_id,
            metadata=metadata,
        )

    async def promo_credit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Начислить бонус промокода."""

        return await self.credit(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=BalanceTransactionType.PROMO,
            description=description,
            idempotency_key=idempotency_key,
            source_type="promo",
            source_id=source_id,
            metadata=metadata,
        )

    async def admin_credit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Ручное зачисление администратором."""

        return await self.credit(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=(
                BalanceTransactionType.ADMIN_CREDIT
            ),
            description=description,
            idempotency_key=idempotency_key,
            source_type="admin",
            source_id=source_id,
            metadata=metadata,
        )

    async def admin_debit(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Ручное списание администратором."""

        return await self.debit(
            session,
            user_id=user_id,
            amount_usd=amount_usd,
            transaction_type=(
                BalanceTransactionType.ADMIN_DEBIT
            ),
            description=description,
            idempotency_key=idempotency_key,
            source_type="admin",
            source_id=source_id,
            metadata=metadata,
        )

    async def adjust(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        amount_usd: Decimal,
        description: str,
        idempotency_key: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BalanceOperationResult:
        """Сделать положительную или отрицательную корректировку."""

        amount = Decimal(str(amount_usd))

        if amount > Decimal("0"):
            return await self.credit(
                session,
                user_id=user_id,
                amount_usd=amount,
                transaction_type=(
                    BalanceTransactionType.ADJUSTMENT
                ),
                description=description,
                idempotency_key=idempotency_key,
                source_type="adjustment",
                source_id=source_id,
                metadata=metadata,
            )

        if amount < Decimal("0"):
            return await self.debit(
                session,
                user_id=user_id,
                amount_usd=abs(amount),
                transaction_type=(
                    BalanceTransactionType.ADJUSTMENT
                ),
                description=description,
                idempotency_key=idempotency_key,
                source_type="adjustment",
                source_id=source_id,
                metadata=metadata,
            )

        raise InvalidBalanceAmountError(
            "Корректировка не может быть равна нулю."
        )

    async def get_balance(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Decimal:
        """Получить баланс пользователя."""

        user = await self._get_user(
            session,
            user_id,
        )

        return Decimal(
            str(user.balance_usd)
        )

    async def get_history(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BalanceTransaction]:
        """Получить историю баланса."""

        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        result = await session.execute(
            select(BalanceTransaction)
            .where(
                BalanceTransaction.user_id == user_id
            )
            .order_by(
                BalanceTransaction.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_transaction(
        self,
        session: AsyncSession,
        transaction_id: int,
    ) -> BalanceTransaction | None:
        """Получить конкретную операцию."""

        result = await session.execute(
            select(BalanceTransaction).where(
                BalanceTransaction.id == transaction_id
            )
        )

        return result.scalar_one_or_none()


balance_service = BalanceService()


__all__ = [
    "BalanceError",
    "InsufficientBalanceError",
    "InvalidBalanceAmountError",
    "BalanceIdempotencyConflictError",
    "BalanceOperationResult",
    "BalanceService",
    "balance_service",
]