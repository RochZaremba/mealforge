from alembic import context

from mealforge.core.config import Settings
from mealforge.core.database import Base, build_engine
from mealforge.households import models as household_models  # noqa: F401
from mealforge.identity import models as identity_models  # noqa: F401
from mealforge.recipes import models as recipe_models  # noqa: F401
from mealforge.recipes.links import models as recipe_links_models  # noqa: F401
from mealforge.reference import models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = build_engine(Settings.from_environment(), migration=True)
    if engine is None:
        raise RuntimeError("Brak konfiguracji bazy danych.")
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql", target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
