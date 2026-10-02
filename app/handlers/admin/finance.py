from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.admin import AdminCB
from app.config import settings
from app.database.models import (
    BalanceTransaction,
    BalanceTransactionType,
    PaymentGateway,
    PaymentInvoice,
    PaymentStatus,
    TopupStatus,
    TopupTransaction,
)
from app.keyboards.admin import admin_main_keyboard
from app.utils.money import format_usd


router = Router(name="admin_finance")


def _is_admin(user_id: int) -> bool:
    """Проверяет права администратора."""
    return user_id in settings.admin_ids


def _enum_value(value: object) -> str:
    """Безопасно получает значение enum."""
    return getattr(value, "value", str(value))


def _format_datetime(value: datetime | None) -> str:
    """Форматирует дату/время для Telegram."""
    if value is None:
        return "—"

    return value.astimezone(timezone.utc).strftime(
        "%d.%m.%Y %H:%M"
    )


def _format_gateway(value: object) -> str:
    """Возвращает человекочитаемое название шлюза."""
    raw = _enum_value(value)

    names = {
        "cryptopay": "CryptoPay",
        "nowpayments": "NOWPayments",
        "crypto_pay": "CryptoPay",
        "now_payments": "NOWPayments",
    }

    return names.get(raw.lower(), raw)


def _format_transaction_type(
    value: BalanceTransactionType,
) -> str:
    """Возвращает название типа операции."""
    names = {
        BalanceTransactionType.DEPOSIT: "Пополнение",
        BalanceTransactionType.WITHDRAWAL: "Списание",
        BalanceTransactionType.PAYMENT: "Оплата",
        BalanceTransactionType.REFUND: "Возврат",
        BalanceTransactionType.ADMIN_ADJUSTMENT: (
            "Корректировка администратором"
        ),
        BalanceTransactionType.REFERRAL_REWARD: (
            "Реферальное вознаграждение"
        ),
        BalanceTransactionType.PROMO: (
            "Промокод"
        ),
    }

    return names.get(
        value,
        _enum_value(value),
    )


async def _get_balance_summary(
    session: AsyncSession,
) -> tuple[Decimal, Decimal, Decimal]:
    """Возвращает общий баланс, пополнения и списания."""
    total_balance = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    # Баланс хранится непосредственно в User,
                    # поэтому здесь агрегируем через подзапрос.
                    0
                ),
                0,
            )
        )
    )

    # Суммы по операциям баланса.
    deposits = await session.scalar(
        select(
            func.coalesce(
                func.sum(BalanceTransaction.amount_usd),
                0,
            )
        ).where(
            BalanceTransaction.type
            == BalanceTransactionType.DEPOSIT
        )
    )

    withdrawals = await session.scalar(
        select(
            func.coalesce(
                func.sum(BalanceTransaction.amount_usd),
                0,
            )
        ).where(
            BalanceTransaction.type
            == BalanceTransactionType.WITHDRAWAL
        )
    )

    return (
        Decimal(str(total_balance or 0)),
        Decimal(str(deposits or 0)),
        Decimal(str(withdrawals or 0)),
    )


async def _get_invoice_stats(
    session: AsyncSession,
) -> dict[str, int]:
    """Статистика платёжных инвойсов."""
    total = await session.scalar(
        select(func.count(PaymentInvoice.id))
    )

    pending = await session.scalar(
        select(func.count(PaymentInvoice.id)).where(
            PaymentInvoice.status == PaymentStatus.PENDING
        )
    )

    paid = await session.scalar(
        select(func.count(PaymentInvoice.id)).where(
            PaymentInvoice.status == PaymentStatus.PAID
        )
    )

    return {
        "total": int(total or 0),
        "pending": int(pending or 0),
        "paid": int(paid or 0),
    }


async def _get_topup_stats(
    session: AsyncSession,
) -> dict[str, Decimal | int]:
    """Статистика пополнений."""
    total = await session.scalar(
        select(func.count(TopupTransaction.id))
    )

    pending = await session.scalar(
        select(func.count(TopupTransaction.id)).where(
            TopupTransaction.status == TopupStatus.PENDING
        )
    )

    paid = await session.scalar(
        select(func.count(TopupTransaction.id)).where(
            TopupTransaction.status == TopupStatus.PAID
        )
    )

    amount = await session.scalar(
        select(
            func.coalesce(
                func.sum(TopupTransaction.amount_usd),
                0,
            )
        ).where(
            TopupTransaction.status == TopupStatus.PAID
        )
    )

    return {
        "total": int(total or 0),
        "pending": int(pending or 0),
        "paid": int(paid or 0),
        "amount": Decimal(str(amount or 0)),
    }


async def _build_finance_text(
    session: AsyncSession,
) -> str:
    """Формирует финансовую сводку."""
    invoice_stats = await _get_invoice_stats(session)
    topup_stats = await _get_topup_stats(session)

    deposits = await session.scalar(
        select(
            func.coalesce(
                func.sum(BalanceTransaction.amount_usd),
                0,
            )
        ).where(
            BalanceTransaction.type
            == BalanceTransactionType.DEPOSIT
        )
    )

    payments = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    BalanceTransaction.amount_usd
                ),
                0,
            )
        ).where(
            BalanceTransaction.type
            == BalanceTransactionType.PAYMENT
        )
    )

    refunds = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    BalanceTransaction.amount_usd
                ),
                0,
            )
        ).where(
            BalanceTransaction.type
            == BalanceTransactionType.REFUND
        )
    )

    transactions_count = await session.scalar(
        select(
            func.count(BalanceTransaction.id)
        )
    )

    return (
        "💰 <b>Финансы</b>\n\n"

        "💳 <b>Платежи</b>\n"
        f"├ Инвойсов: "
        f"<b>{invoice_stats['total']}</b>\n"
        f"├ Ожидают: "
        f"<b>{invoice_stats['pending']}</b>\n"
        f"└ Оплачены: "
        f"<b>{invoice_stats['paid']}</b>\n\n"

        "💵 <b>Баланс</b>\n"
        f"├ Пополнено: "
        f"<b>{format_usd(Decimal(str(deposits or 0)))}</b>\n"
        f"├ Оплачено с баланса: "
        f"<b>{format_usd(Decimal(str(payments or 0)))}</b>\n"
        f"└ Возвращено: "
        f"<b>{format_usd(Decimal(str(refunds or 0)))}</b>\n\n"

        "📥 <b>Пополнения</b>\n"
        f"├ Всего операций: "
        f"<b>{topup_stats['total']}</b>\n"
        f"├ Ожидают: "
        f"<b>{topup_stats['pending']}</b>\n"
        f"├ Успешных: "
        f"<b>{topup_stats['paid']}</b>\n"
        f"└ Сумма: "
        f"<b>{format_usd(topup_stats['amount'])}</b>\n\n"

        f"📊 Всего операций баланса: "
        f"<b>{transactions_count or 0}</b>"
    )


@router.message(Command("finance"))
async def finance_command(
    message: Message,
    session: AsyncSession,
) -> None:
    """Открывает финансовую статистику."""
    if message.from_user is None:
        return

    if not _is_admin(message.from_user.id):
        return

    try:
        text = await _build_finance_text(session)

        await message.answer(
            text,
            reply_markup=admin_main_keyboard(),
        )

    except Exception:
        logger.exception(
            "Ошибка открытия финансов: admin={}",
            message.from_user.id,
        )

        await message.answer(
            "❌ Не удалось загрузить финансовую статистику."
        )


@router.callback_query(
    AdminCB.filter(F.action == "finance")
)
async def finance_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Открывает финансы из админ-меню."""
    if callback.from_user is None:
        return

    if not _is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    try:
        text = await _build_finance_text(session)

        if callback.message is not None:
            await callback.message.edit_text(
                text,
                reply_markup=admin_main_keyboard(),
            )

        await callback.answer()

    except Exception:
        logger.exception(
            "Ошибка открытия финансов: admin={}",
            callback.from_user.id,
        )

        await callback.answer(
            "Ошибка загрузки финансов.",
            show_alert=True,
        )


@router.callback_query(
    AdminCB.filter(F.action == "finance_invoices")
)
async def finance_invoices_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Показывает последние платёжные инвойсы."""
    if callback.from_user is None:
        return

    if not _is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    try:
        result = await session.scalars(
            select(PaymentInvoice)
            .order_by(
                PaymentInvoice.created_at.desc()
            )
            .limit(20)
        )

        invoices = list(result)

        if not invoices:
            text = (
                "💳 <b>Последние инвойсы</b>\n\n"
                "Инвойсов пока нет."
            )
        else:
            lines = [
                "💳 <b>Последние инвойсы</b>\n"
            ]

            for invoice in invoices:
                status = _enum_value(
                    invoice.status
                )

                gateway = _format_gateway(
                    invoice.gateway
                )

                crypto_currency = (
                    invoice.crypto_currency
                    or "—"
                )

                lines.append(
                    f"#{invoice.id} | "
                    f"<b>{format_usd(invoice.amount_usd)}</b>\n"
                    f"├ Статус: "
                    f"<code>{status}</code>\n"
                    f"├ Шлюз: "
                    f"<code>{gateway}</code>\n"
                    f"├ Валюта: "
                    f"<code>{crypto_currency}</code>\n"
                    f"└ Создан: "
                    f"<code>"
                    f"{_format_datetime(invoice.created_at)}"
                    f"</code>\n"
                )

            text = "\n".join(lines)

        if callback.message is not None:
            await callback.message.edit_text(
                text,
                reply_markup=admin_main_keyboard(),
            )

        await callback.answer()

    except Exception:
        logger.exception(
            "Ошибка загрузки инвойсов: admin={}",
            callback.from_user.id,
        )

        await callback.answer(
            "Ошибка загрузки инвойсов.",
            show_alert=True,
        )


@router.callback_query(
    AdminCB.filter(F.action == "finance_topups")
)
async def finance_topups_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Показывает последние пополнения."""
    if callback.from_user is None:
        return

    if not _is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    try:
        result = await session.scalars(
            select(TopupTransaction)
            .order_by(
                TopupTransaction.created_at.desc()
            )
            .limit(20)
        )

        topups = list(result)

        if not topups:
            text = (
                "📥 <b>Последние пополнения</b>\n\n"
                "Пополнений пока нет."
            )
        else:
            lines = [
                "📥 <b>Последние пополнения</b>\n"
            ]

            for topup in topups:
                status = _enum_value(
                    topup.status
                )

                asset = (
                    topup.crypto_currency
                    if hasattr(
                        topup,
                        "crypto_currency",
                    )
                    else getattr(
                        topup,
                        "asset",
                        "—",
                    )
                )

                lines.append(
                    f"#{topup.id} | "
                    f"<b>{format_usd(topup.amount_usd)}</b>\n"
                    f"├ Статус: "
                    f"<code>{status}</code>\n"
                    f"├ Крипто: "
                    f"<code>{asset or '—'}</code>\n"
                    f"└ Создано: "
                    f"<code>"
                    f"{_format_datetime(topup.created_at)}"
                    f"</code>\n"
                )

            text = "\n".join(lines)

        if callback.message is not None:
            await callback.message.edit_text(
                text,
                reply_markup=admin_main_keyboard(),
            )

        await callback.answer()

    except Exception:
        logger.exception(
            "Ошибка загрузки пополнений: admin={}",
            callback.from_user.id,
        )

        await callback.answer(
            "Ошибка загрузки пополнений.",
            show_alert=True,
        )


__all__ = ["router"]