from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded .env file: {env_path}")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get DATABASE_URL from environment variable
# Alembic requires synchronous driver (psycopg2), not asyncpg
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Convert postgresql+asyncpg:// to postgresql+psycopg2:// for Alembic
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        print(f"[INFO] Converted asyncpg URL to psycopg2 for Alembic")
    # Remove sslmode parameter if present (psycopg2 uses ssl parameter differently)
    # Actually, psycopg2 supports sslmode, so we can keep it
    config.set_main_option("sqlalchemy.url", database_url)
    print(f"[OK] DATABASE_URL configured")
else:
    print(f"[WARNING] DATABASE_URL environment variable not set")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all domain models for autogenerate
from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]
from app.domain.v1.minso.models import (  # pyright: ignore[reportMissingImports]
    Problem,
    ReferenceAnswer,
    Issue,
    UserAnswer,
    AnswerStructure,
    ReasoningTask,
    ReasoningResult,
    Feedback,
    FeedbackItem,
    FeedbackEmbedding,
    ReferenceAnswerEmbedding,
    UserAnswerEmbedding,
    ReasoningTaskEmbedding,
)
from training.models import TrainingData, TrainingJob, ModelVersion  # pyright: ignore[reportMissingImports]

# Set target_metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
