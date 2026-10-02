from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import create_engine

import importlib.util
import sys
from pathlib import Path


# Загружаем модели напрямую, не импортируя app.database.__init__.py.
# Это исключает запуск runtime AsyncEngine во время миграций.
_models_path = Path(__file__).resolve().parents[1] / "app" / "database" / "models.py"
_models_spec = importlib.util.spec_from_file_location("alembic_models", _models_path)
if _models_spec is None or _models_spec.loader is None:
    raise RuntimeError(f"Не удалось загрузить модели: {_models_path}")
_models_module = importlib.util.module_from_spec(_models_spec)
sys.modules[_models_spec.name] = _models_module
_models_spec.loader.exec_module(_models_module)
Base = _models_module.Base


# ============================================================
# ALEMBIC CONFIGURATION
# ============================================================

config = context.config


# ============================================================
# LOGGING
# ============================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# SQLALCHEMY METADATA
# ============================================================

target_metadata = Base.metadata


# ============================================================
# DATABASE URL
# ============================================================

def get_database_url() -> str:
    """
    Получает URL базы данных.

    Приоритет:
    1. DATABASE_URL из окружения;
    2. sqlalchemy.url из alembic.ini.
    """

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    database_url = config.get_main_option("sqlalchemy.url")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL не указан."
        )

    return database_url


# ============================================================
# OFFLINE MIGRATIONS
# ============================================================

def run_migrations_offline() -> None:
    """
    Выполняет миграции без подключения к БД.

    Используется для генерации SQL-скрипта миграции.
    """

    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# ONLINE MIGRATIONS
# ============================================================

def do_run_migrations(
    connection: Connection,
) -> None:
    """
    Выполняет миграции через существующее
    синхронное SQLAlchemy-соединение.
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_online_migrations() -> None:
    """Выполнить миграции через обычный синхронный SQLAlchemy engine.

    Alembic не должен зависеть от async-драйвера приложения.
    URL async-драйверов автоматически преобразуется в sync-вариант.
    """

    database_url = get_database_url()

    database_url = database_url.replace(
        "+aiosqlite",
        "",
    ).replace(
        "+asyncpg",
        "+psycopg",
    )

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            do_run_migrations(connection)
    finally:
        connectable.dispose()


def run_migrations_online() -> None:
    """
    Точка входа для online-миграций.
    """

    run_online_migrations()


# ============================================================
# ENTRY POINT
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()