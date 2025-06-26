from __future__ import annotations
import asyncio, logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.steps_bot.settings import config
from app.steps_bot.db.models import Base

fileConfig(context.config.config_file_name)
logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def db_url() -> str:
    return (
        f"postgresql+asyncpg://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}"
        f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
    )


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name.startswith(("auth_", "django_", "sessions")):
        return False

    if type_ == "type" and name in {"mediatype", "userrole", "walkform"}:
        return False

    return True


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(db_url(), poolclass=pool.NullPool)

    async with connectable.connect() as conn:
        await conn.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
