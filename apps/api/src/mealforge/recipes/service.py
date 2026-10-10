import json
from hashlib import sha256
from importlib.resources import files
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from mealforge.core.api import ApiError, now
from mealforge.households.routes import decimal_text
from mealforge.recipes.models import Recipe, RecipeVersion
from mealforge.recipes.schemas import IngredientInput, RecipeInput, RecipeSnapshot, UnknownNutrients

WARNINGS = [
    {"code": "NUTRIENTS_UNKNOWN", "message": "Brak identyfikowalnych danych o energii i makro."},
    {
        "code": "ALLERGENS_UNKNOWN",
        "message": "Nie zweryfikowano alergenów ani bezpieczeństwa dla alergii.",
    },
    {"code": "YIELD_UNKNOWN", "message": "Nie zmierzono masy gotowej potrawy."},
]
EXPECTED_FIXTURE_SHA256 = "45dbdc9c13bca1b38a458e65297430f58371a7ddce8cf574f165f096219a98b1"


def snapshot(
    payload: RecipeInput,
    author: str,
    previous: RecipeVersion | None = None,
    original: dict[str, Any] | None = None,
) -> dict[str, Any]:
    origin = None
    if original:
        provenance = original["provenance"]
        origin = {
            "source_id": "original_fixture",
            "fixture_id": original["id"],
            "author": "MealForge",
            "license": "CC0-1.0",
            "license_scope": "original_recipe_text",
            "attribution": provenance["attribution"],
        }
    elif previous:
        previous_origin = RecipeSnapshot.model_validate(
            previous.snapshot
        ).provenance.original_origin
        origin = previous_origin.model_dump(mode="json") if previous_origin else None
    data = {
        "title": payload.title,
        "instructions": payload.instructions,
        "ingredients": [
            {
                "name": item.name,
                "amount": decimal_text(item.amount),
                "unit": item.unit,
                "weight_state": item.weight_state,
                "nutrients_per_100g": UnknownNutrients().model_dump(),
                "nutrient_provenance": None,
                "allergen_status": "unknown",
            }
            for item in payload.ingredients
        ],
        "provenance": {
            "source_mode": "user_authored",
            "source_id": "original_fixture" if original else "private_user_content",
            "author": "MealForge" if original else author,
            "rights_mode": "private_user_content",
            "license": "CC0-1.0" if original else None,
            "license_scope": "original_recipe_text" if original else None,
            "attribution": original["provenance"]["attribution"] if original else None,
            "rights_attestation": None if original else payload.rights_attestation,
            "source_version_id": str(previous.id) if previous else None,
            "original_origin": origin,
        },
        "nutrients": UnknownNutrients().model_dump(),
        "allergen_status": "unknown",
        "yield_mass_g": None,
        "yield_basis": "unknown_until_weighed",
        "servings": 2 if original else None,
        "servings_basis": "intentional_recipe_design" if original else "unknown",
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "storage_method": None,
        "storage_validation_ref": None,
        "prices": None,
        "status": "draft_requires_review",
        "planner_eligible": False,
        "warnings": WARNINGS,
    }
    return RecipeSnapshot.model_validate(data).model_dump(mode="json")


def append_version(db: Session, recipe: Recipe, actor: UUID, data: dict[str, Any]) -> RecipeVersion:
    version = RecipeVersion(
        recipe_id=recipe.id,
        household_id=recipe.household_id,
        version=recipe.current_version,
        snapshot=RecipeSnapshot.model_validate(data).model_dump(mode="json"),
        created_at=now(),
        actor_user_id=actor,
    )
    db.add(version)
    db.flush()
    return version


def new_recipe(db: Session, household: UUID, actor: UUID, data: dict[str, Any]) -> RecipeVersion:
    recipe = Recipe(household_id=household, current_version=1, created_at=now())
    db.add(recipe)
    db.flush()  # Deferred current-version FK is checked when the complete transaction commits.
    return append_version(db, recipe, actor, data)


def original_snapshots() -> list[dict[str, Any]]:
    """Ship the whole audited fixture; missing or invalid resources abort the demo transaction."""
    try:
        resource = files("mealforge.recipes").joinpath("originals.json")
        with resource.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        data = json.loads(raw)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if sha256(canonical.encode("utf-8")).hexdigest() != EXPECTED_FIXTURE_SHA256:
            raise ValueError
        if data["schema_version"] != 1 or data["fixture_only"] is not True:
            raise ValueError
        originals = data["recipes"]
        expected = {
            "original-millet-apple",
            "original-lentil-carrot",
            "original-cucumber-tomato-sandwiches",
        }
        if len(originals) != 3 or {row["id"] for row in originals} != expected:
            raise ValueError
        result = []
        for row in originals:
            provenance = row["provenance"]
            if (
                provenance["source_id"] != "original_fixture"
                or provenance["author"] != "MealForge"
                or provenance["license"] != "CC0-1.0"
                or provenance["license_scope"] != "original_recipe_text"
                or row["source_mode"] != "user_authored"
                or row["source_url"] is not None
                or row["validation_status"] != "draft_requires_review"
                or row["servings"] != 2
                or row["servings_basis"] != "intentional_recipe_design"
                or row["yield_mass_g"] is not None
                or row["allergen_status"] != "unknown"
            ):
                raise ValueError
            UnknownNutrients.model_validate(row["nutrients"])
            for field in (
                "storage_method",
                "storage_validation_ref",
                "price",
                "prep_time_min",
                "cook_time_min",
            ):
                if row[field] is not None:
                    raise ValueError
            ingredients = []
            for item in row["ingredients"]:
                UnknownNutrients.model_validate(item["nutrients_per_100g"])
                if item["nutrient_provenance"] is not None or item["allergen_status"] != "unknown":
                    raise ValueError
                ingredients.append(
                    IngredientInput(
                        name=item["raw_name"],
                        amount=item["amount"],
                        unit=item["unit"],
                        weight_state=item["raw_or_cooked"],
                    )
                )
            payload = RecipeInput(
                title=row["title"],
                instructions=row["instructions"],
                ingredients=ingredients,
                rights_attestation="i_am_author",
            )
            result.append(snapshot(payload, "MealForge", original=row))
        return result
    except (OSError, KeyError, TypeError, ValueError, ValidationError):
        raise ApiError(
            503, "DEMO_FIXTURE_UNAVAILABLE", "Dane demonstracyjne nie są dostępne."
        ) from None
