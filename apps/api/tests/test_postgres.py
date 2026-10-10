import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from mealforge.core.config import Settings
from mealforge.core.database import database_is_ready, migration_config, session_factory
from mealforge.main import create_app
from mealforge.reference.models import MealSlotDefinition
from mealforge.seed import seed_reference_data

pytestmark = pytest.mark.integration


def test_ready_requires_schema_and_tracks_downgrade(postgres_settings: Settings) -> None:
    with TestClient(create_app(postgres_settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        command.upgrade(migration_config(), "head")
        assert client.get("/ready").json() == {"status": "ready"}
        command.downgrade(migration_config(), "base")
        assert client.get("/ready").status_code == 503
        command.upgrade(migration_config(), "head")
        assert client.get("/ready").status_code == 200
        command.check(migration_config())


def test_reference_seed_is_idempotent_and_non_private(
    postgres_settings: Settings, migrated_engine: Engine
) -> None:
    seed_reference_data(postgres_settings)
    seed_reference_data(postgres_settings)
    with migrated_engine.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(MealSlotDefinition))
        names = (
            connection.execute(
                select(MealSlotDefinition.display_name).order_by(MealSlotDefinition.position)
            )
            .scalars()
            .all()
        )
    assert count == 5
    assert names == ["Śniadanie", "Drugie śniadanie", "Obiad", "Przekąska", "Kolacja"]
    assert set(inspect(migrated_engine).get_table_names()) == {
        "alembic_version",
        "meal_slot_definitions",
    }


def test_persistence_unit_of_work_rolls_back(migrated_engine: Engine) -> None:
    factory = session_factory(migrated_engine)
    with pytest.raises(IntegrityError):
        with factory.begin() as session:
            session.add(MealSlotDefinition(code="valid", display_name="Poprawny", position=0))
            session.flush()
            session.add(MealSlotDefinition(code="invalid", display_name="Błędny", position=-1))
            session.flush()
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(MealSlotDefinition)) == 0


def test_unexpected_migration_revision_is_not_ready(migrated_engine: Engine) -> None:
    assert database_is_ready(migrated_engine)
    with migrated_engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='unknown_revision'"))
    assert not database_is_ready(migrated_engine)
