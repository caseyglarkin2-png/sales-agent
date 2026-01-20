"""Alembic environment configuration."""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from src.db import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    connectable = config.get_section(config.config_ini_section)

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Helper to run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from src.config import get_settings

    settings = get_settings()
    configuration = config.get_section(config.config_ini_section)
    
    # Use async database URL for asyncpg driver
    db_url = settings.async_database_url
    configuration["sqlalchemy.url"] = db_url

    connectable = create_async_engine(
        db_url, poolclass=pool.NullPool, echo=False
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
