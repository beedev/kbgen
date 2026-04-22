"""Alembic env — sync DATABASE_URL override, kb schema ownership."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.config import get_settings
from src.storage.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the ini URL with runtime env (convert asyncpg → psycopg for sync Alembic).
runtime_url = get_settings().database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", runtime_url)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Only manage objects in the kb schema."""
    if type_ == "table" and obj.schema != "kb":
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=include_object,
        version_table_schema="kb",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Ensure the schema Alembic writes `alembic_version` into exists before
        # the version table create runs.
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS kb")
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema="kb",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
