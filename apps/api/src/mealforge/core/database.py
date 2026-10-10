from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from mealforge.core.config import Settings


class Base(DeclarativeBase):
    pass


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    return config


def build_engine(settings: Settings, *, migration: bool = False) -> Engine | None:
    if settings.database_url is None:
        return None
    arguments = {"connect_timeout": 3, "options": "-c statement_timeout=3000 -c lock_timeout=3000"}
    if migration:
        return create_engine(
            settings.database_url.get_secret_value(),
            poolclass=NullPool,
            connect_args=arguments,
            hide_parameters=True,
        )
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=3,
        connect_args=arguments,
        hide_parameters=True,
    )


def database_is_ready(engine: Engine | None) -> bool:
    if engine is None:
        return False
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        current = set(MigrationContext.configure(connection).get_current_heads())
    return bool(expected) and current == expected


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Services use `with factory.begin() as session` for atomic units of work."""
    return sessionmaker(bind=engine, expire_on_commit=False)
