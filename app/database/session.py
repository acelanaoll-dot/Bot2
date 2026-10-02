from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def _create_engine() -> AsyncEngine:
    """Создать асинхронный SQLAlchemy engine."""

    database_url = settings.database_url

    if settings.is_sqlite:
        engine = create_async_engine(
            database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            connect_args={
                "timeout": 30,
            },
        )

        _configure_sqlite(engine)

        logger.info("Создан SQLite async engine")
        return engine

    if settings.is_postgresql:
        engine = create_async_engine(
            database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
        )

        logger.info("Создан PostgreSQL async engine")
        return engine

    raise RuntimeError(
        f"Неподдерживаемый тип базы данных: {database_url}"
    )


def _configure_sqlite(engine: AsyncEngine) -> None:
    """Настроить SQLite для конкурентной работы."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(
        dbapi_connection: object,
        connection_record: object,
    ) -> None:
        del connection_record

        cursor = dbapi_connection.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


engine: AsyncEngine = _create_engine()


SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Получить обычную async-сессию.

    Транзакция здесь не открывается автоматически.
    Это позволяет middleware и сервисам самостоятельно
    управлять границами транзакций.
    """

    session = SessionLocal()

    try:
        yield session

    except Exception:
        if session.in_transaction():
            await session.rollback()

        logger.exception(
            "Ошибка во время работы сессии БД"
        )
        raise

    finally:
        await session.close()


@asynccontextmanager
async def write_transaction(
    session: AsyncSession | None = None,
) -> AsyncIterator[AsyncSession]:
    """
    Открыть транзакцию записи.

    Если передана существующая AsyncSession, используется именно она.
    Это важно для сервисов: несколько операций должны выполняться
    в одной транзакции и одной сессии.

    Если в переданной сессии транзакция уже открыта, создаётся
    логическая вложенная область без отдельного commit/rollback;
    результатом управляет внешняя транзакция.
    """

    owns_session = session is None
    active_session = session or SessionLocal()
    owns_transaction = False

    try:
        if active_session.in_transaction():
            yield active_session
            return

        if settings.is_sqlite:
            await active_session.execute(text("BEGIN IMMEDIATE"))
        else:
            await active_session.begin()

        owns_transaction = True

        try:
            yield active_session
        except Exception:
            if active_session.in_transaction():
                await active_session.rollback()
            raise
        else:
            if active_session.in_transaction():
                await active_session.commit()

    except Exception:
        logger.exception("Ошибка транзакции записи в БД")
        raise

    finally:
        if owns_session:
            await active_session.close()
        elif not owns_transaction:
            # Вложенная область ничего не закрывает и не коммитит.
            pass


async def begin_immediate(
    session: AsyncSession,
) -> None:
    """
    Явно начать write-транзакцию SQLite.

    Используется только там, где сессия уже создана
    и сервису нужен контроль над границами транзакции.
    """

    if session.in_transaction():
        raise RuntimeError(
            "Нельзя выполнить BEGIN IMMEDIATE: "
            "транзакция уже открыта."
        )

    if settings.is_sqlite:
        await session.execute(
            text("BEGIN IMMEDIATE")
        )
        return

    await session.begin()


async def check_database_connection() -> bool:
    """Проверить доступность базы данных."""

    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))

        logger.debug(
            "Проверка подключения к БД успешно пройдена"
        )
        return True

    except Exception:
        logger.exception(
            "Не удалось подключиться к базе данных"
        )
        return False


async def init_database() -> None:
    """
    Проверить доступность БД.

    Создание таблиц здесь специально не выполняется:
    схема управляется Alembic.
    """

    try:
        is_available = await check_database_connection()

        if not is_available:
            raise RuntimeError(
                "База данных недоступна."
            )

        logger.info(
            "База данных доступна"
        )

    except Exception:
        logger.exception(
            "Ошибка инициализации базы данных"
        )
        raise


async def dispose_database() -> None:
    """Корректно закрыть connection pool."""

    try:
        await engine.dispose()

        logger.info(
            "Соединения с базой данных закрыты"
        )

    except Exception:
        logger.exception(
            "Ошибка при закрытии соединений "
            "с базой данных"
        )
        raise


__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "write_transaction",
    "begin_immediate",
    "check_database_connection",
    "init_database",
    "dispose_database",
]