import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from mealforge.core.config import Settings
from mealforge.core.database import build_engine, migration_config


@pytest.fixture
def postgres_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Every test owns a new database; never downgrade developer/production databases."""
    source = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not source:
        pytest.skip("PostgreSQL integration needs TEST_DATABASE_URL or DATABASE_URL")
    database_name = "mealforge_test_" + uuid4().hex
    url = make_url(source)
    admin = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    except SQLAlchemyError:
        admin.dispose()
        raise RuntimeError("Nie udało się utworzyć izolowanej bazy testowej PostgreSQL.") from None
    test_url = url.set(database=database_name).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", test_url)
    try:
        yield Settings(database_url=SecretStr(test_url))
    finally:
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE "{database_name}"'))
        admin.dispose()


@pytest.fixture
def migrated_engine(postgres_settings: Settings) -> Iterator[Engine]:
    command.upgrade(migration_config(), "head")
    engine = build_engine(postgres_settings)
    assert engine is not None
    try:
        yield engine
    finally:
        engine.dispose()
