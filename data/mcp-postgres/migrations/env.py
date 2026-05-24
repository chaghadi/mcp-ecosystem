"""
migrations/env.py — Alembic migration environment.

Reads DATABASE_URL from the environment so the same migrations work
against Supabase (now) and DigitalOcean PostgreSQL (later).
The only change required to migrate hosts is the DATABASE_URL env var.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object — access alembic.ini values via config.get_main_option()
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── DATABASE_URL ──────────────────────────────────────────────────────────────
# Read from environment — never hardcode credentials here.
database_url = os.environ.get("DATABASE_URL", "")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Copy .env.example to .env and add your connection string, "
        "then run: uv run alembic upgrade head"
    )

config.set_main_option("sqlalchemy.url", database_url)

# ── Target metadata ───────────────────────────────────────────────────────────
# Import your SQLAlchemy models here when you have them, to enable autogenerate.
# Example:
#   from src.models import Base
#   target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without a live connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — apply directly to the database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
