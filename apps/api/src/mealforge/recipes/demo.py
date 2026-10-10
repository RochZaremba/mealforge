from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from mealforge.core.api import PROBLEM_RESPONSES, Configuration, Db, audit, mutate, now
from mealforge.households.authorization import authorize
from mealforge.households.models import Household, HouseholdMember, MealSlotPreset, NutritionProfile
from mealforge.households.routes import household_dto
from mealforge.identity.routes import Auth, require_mutation
from mealforge.recipes.schemas import DemoInput, DemoResponse
from mealforge.recipes.service import new_recipe, original_snapshots
from mealforge.seed import MEAL_SLOT_DEFINITIONS

router = APIRouter(prefix="/api/v1/households", tags=["demo"], responses=PROBLEM_RESPONSES)


@router.post("/demo", status_code=201, response_model=DemoResponse)
def create_demo(
    payload: DemoInput, request: Request, db: Db, auth: Auth, settings: Configuration
) -> dict[str, Any]:
    require_mutation(request, settings, auth)

    def operation() -> dict[str, Any]:
        originals = original_snapshots()  # Validate all three before writing anything.
        household = Household(
            name="Kuchnia demonstracyjna",
            owner_user_id=auth.user.id,
            timezone="Europe/Warsaw",
            currency="PLN",
            source="demo_seed",
            slot_revision=1,
            created_at=now(),
        )
        db.add(household)
        db.flush()
        for user_id, name, role, kcal in (
            (auth.user.id, auth.user.display_name, "owner", "2700"),
            (None, "Druga osoba (demo)", "viewer", "1600"),
        ):
            member = HouseholdMember(
                household_id=household.id,
                user_id=user_id,
                display_name=name,
                role=role,
                is_guest=False,
                active=True,
                target_revision=1,
            )
            db.add(member)
            db.flush()
            profile = NutritionProfile(
                household_id=household.id,
                member_id=member.id,
                version=1,
                kcal_target=Decimal(kcal),
                protein_target_g=None,
                carbs_target_g=None,
                fat_target_g=None,
                goal_type="custom",
                source="demo_seed",
                valid_from=now().astimezone(ZoneInfo(household.timezone)).date(),
                created_at=now(),
                actor_user_id=auth.user.id,
            )
            db.add(profile)
            db.flush()
            audit(
                db,
                request,
                auth.user.id,
                household.id,
                "nutrition_target.demo_created",
                "nutrition_profile",
                profile.id,
                None,
                1,
            )
        for ordering, (code, name) in enumerate(MEAL_SLOT_DEFINITIONS):
            db.add(
                MealSlotPreset(
                    household_id=household.id,
                    name=name,
                    ordering=ordering,
                    default_time=None,
                    default_share=None,
                    repeat_weekly=code in {"breakfast", "dinner"},
                    active=True,
                )
            )
        for data in originals:
            version = new_recipe(db, household.id, auth.user.id, data)
            audit(
                db,
                request,
                auth.user.id,
                household.id,
                "recipe.demo_created",
                "recipe",
                version.recipe_id,
                None,
                1,
            )
        audit(
            db,
            request,
            auth.user.id,
            household.id,
            "household.demo_created",
            "household",
            household.id,
        )
        return {"household_id": str(household.id)}

    def replay_authorize(reference: dict[str, Any]) -> None:
        if "household_id" not in reference:
            from mealforge.core.api import ApiError

            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Identyfikator operacji został już użyty.")
        authorize(db, auth, UUID(reference["household_id"]), owner=True)

    reference = mutate(
        db,
        request,
        auth.user.id,
        "user",
        "household.demo",
        payload.model_dump(mode="json"),
        operation,
        replay_authorize,
    )
    household_id = UUID(reference["household_id"])
    member = authorize(db, auth, household_id, owner=True)
    household = db.get(Household, household_id)
    assert household is not None
    return {"household": household_dto(household, member)}
