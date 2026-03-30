"""
Alembic environment configuration.

Loads .env, imports all SQLAlchemy models so that Base.metadata reflects
the full schema, and wires in the database URL from app settings.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# 1. Ensure the backend root is on sys.path so "app.*" imports work.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# 2. Load .env file so DB_* vars are available to Settings.
# ---------------------------------------------------------------------------
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key:
            os.environ.setdefault(key, value)

# ---------------------------------------------------------------------------
# 3. Import Base *and* every model module so metadata is fully populated.
#    Adding or removing a model file? Just update app/models/__init__.py.
# ---------------------------------------------------------------------------
from app.db import Base  # noqa: E402
import app.models  # noqa: E402, F401  — triggers all model imports

# ---------------------------------------------------------------------------
# 4. Alembic setup.
# ---------------------------------------------------------------------------
config = context.config

# Python logging from the .ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide the real DB URL to Alembic (overrides sqlalchemy.url in .ini)
from app.core.settings import get_settings  # noqa: E402

config.set_main_option("sqlalchemy.url", get_settings().database_url)

# The MetaData that Alembic will compare against the live database.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline & online migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script output only)."""
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
    """Run migrations in 'online' mode — connects to the live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
