import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

# импортируем ваш объект settings
from app.core.config import settings
from app.db.base import Base  # или откуда берете metadata ваших моделей

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Если вы хотите, чтобы URL тоже брался из .ini, можно сделать:
# config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Настраиваем логирование согласно alembic.ini
fileConfig(str(config.config_file_name))

# указываем метаданные для автогенерации
target_metadata = Base.metadata


def run_migrations_offline():
    """Запуск миграций в 'offline' режиме."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Запуск миграций в 'online' режиме (асинхронно)."""
    # создаем асинхронный движок на базе нашего URL
    connectable: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # для асинхронного запуска
    asyncio.run(run_migrations_online())
