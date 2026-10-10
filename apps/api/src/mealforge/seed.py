"""Explicit idempotent seed: reference names only, never health/nutrition fixtures."""

from sqlalchemy.dialects.postgresql import insert

from mealforge.core.config import Settings
from mealforge.core.database import build_engine
from mealforge.reference.models import MealSlotDefinition

MEAL_SLOT_DEFINITIONS = (
    ("breakfast", "Śniadanie"),
    ("second_breakfast", "Drugie śniadanie"),
    ("lunch", "Obiad"),
    ("snack", "Przekąska"),
    ("dinner", "Kolacja"),
)


def seed_reference_data(settings: Settings) -> None:
    engine = build_engine(settings)
    if engine is None:
        raise RuntimeError("Brak konfiguracji bazy danych.")
    try:
        with engine.begin() as connection:
            for position, (code, name) in enumerate(MEAL_SLOT_DEFINITIONS):
                statement = insert(MealSlotDefinition).values(
                    code=code, display_name=name, position=position
                )
                connection.execute(statement.on_conflict_do_nothing(index_elements=["code"]))
    finally:
        engine.dispose()


def main() -> None:
    try:
        seed_reference_data(Settings.from_environment())
    except Exception:
        raise SystemExit("Nie udało się zapisać danych referencyjnych.") from None
    print("Zapisano pięć nazw posiłków; bez danych prywatnych i wartości odżywczych.")


if __name__ == "__main__":
    main()
