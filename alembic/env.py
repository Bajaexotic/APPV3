"""Alembic Environment Configuration

This file configures the Alembic migration environment for APPSIERRA.
It handles both offline and online migration scenarios.
"""

from logging.config import fileConfig
import os
from pathlib import Path
import sys

from sqlalchemy import engine_from_config, pool

from alembic import context


# ============================================================================
# Alembic Configuration
# ============================================================================

config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================================
# Add Project Root to Python Path
# ============================================================================

# Get the project root directory (parent of alembic/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# Import Your Models
# ============================================================================

# TODO: Import your SQLAlchemy models here
# Example:
# from config.database import Base
# from services.trade_models import Trade, Position, Account
#
# For now, we'll create a placeholder Base
from sqlalchemy.orm import declarative_base


Base = declarative_base()

# Set target_metadata to your models' metadata
target_metadata = Base.metadata

# ============================================================================
# Database URL Configuration
# ============================================================================


def get_url():
    """Get database URL from environment or config file."""
    # Priority: Environment variable > Config file
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return config.get_main_option("sqlalchemy.url")


# ============================================================================
# Migration Functions
# ============================================================================


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================================
# Execute Migrations
# ============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
