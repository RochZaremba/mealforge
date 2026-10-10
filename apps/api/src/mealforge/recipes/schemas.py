from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from mealforge.households.schemas import Energy, HouseholdResponse, Input, WarningResponse


class IngredientInput(Input):
    name: str = Field(min_length=1, max_length=160)
    amount: Energy | None
    unit: Literal["g", "ml", "piece", "unknown"]
    weight_state: Literal["raw", "cooked", "as_packaged", "unknown"]

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Znana ilość składnika musi być dodatnia.")
        return value

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Nieprawidłowa nazwa składnika.")
        return value.strip()


class RecipeInput(Input):
    title: str = Field(min_length=1, max_length=160)
    instructions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=30
    )
    ingredients: list[IngredientInput] = Field(min_length=1, max_length=40)
    rights_attestation: Literal["i_am_author"]

    @field_validator("title")
    @classmethod
    def valid_title(cls, value: str) -> str:
        return IngredientInput.nonempty_name(value)

    @field_validator("instructions")
    @classmethod
    def valid_steps(cls, value: list[str]) -> list[str]:
        if any(
            not step.strip() or any(ord(char) < 32 and char not in "\n\t" for char in step)
            for step in value
        ):
            raise ValueError("Nieprawidłowe instrukcje.")
        return [step.strip() for step in value]


class RecipeUpdateInput(RecipeInput):
    expected_version: int = Field(ge=1, strict=True)


class UnknownNutrients(BaseModel):
    kcal: None = None
    protein_g: None = None
    carbs_g: None = None
    fat_g: None = None
    fiber_g: None = None


class IngredientResponse(BaseModel):
    name: str
    amount: str | None
    unit: Literal["g", "ml", "piece", "unknown"]
    weight_state: Literal["raw", "cooked", "as_packaged", "unknown"]
    nutrients_per_100g: UnknownNutrients
    nutrient_provenance: None
    allergen_status: Literal["unknown"]


class OriginalOrigin(BaseModel):
    source_id: Literal["original_fixture"]
    fixture_id: str
    author: Literal["MealForge"]
    license: Literal["CC0-1.0"]
    license_scope: Literal["original_recipe_text"]
    attribution: str


class Provenance(BaseModel):
    source_mode: Literal["user_authored"]
    source_id: Literal["private_user_content", "original_fixture"]
    author: str
    rights_mode: Literal["private_user_content"]
    license: Literal["CC0-1.0"] | None
    license_scope: Literal["original_recipe_text"] | None
    attribution: str | None
    rights_attestation: Literal["i_am_author"] | None
    source_version_id: UUID | None
    original_origin: OriginalOrigin | None


class RecipeSnapshot(BaseModel):
    model_config = {"extra": "forbid"}
    title: str
    instructions: list[str]
    ingredients: list[IngredientResponse]
    provenance: Provenance
    nutrients: UnknownNutrients
    allergen_status: Literal["unknown"]
    yield_mass_g: None
    yield_basis: Literal["unknown_until_weighed"]
    servings: Literal[2] | None
    servings_basis: Literal["unknown", "intentional_recipe_design"]
    prep_time_minutes: None
    cook_time_minutes: None
    storage_method: None
    storage_validation_ref: None
    prices: None
    status: Literal["draft_requires_review"]
    planner_eligible: Literal[False]
    warnings: list[WarningResponse]


class RecipeSummary(BaseModel):
    id: UUID
    household_id: UUID
    version: int
    title: str
    created_at: str
    status: Literal["draft_requires_review"]
    planner_eligible: Literal[False]
    warnings: list[WarningResponse]


class RecipeDetail(RecipeSnapshot):
    id: UUID
    household_id: UUID
    version: int
    version_id: UUID
    created_at: str


class RecipesResponse(BaseModel):
    recipes: list[RecipeSummary]
    next_cursor: UUID | None


class RecipeHistoryResponse(BaseModel):
    history: list[RecipeDetail]
    next_before_version: int | None


class DemoInput(Input):
    confirmation: Literal["create_separate_demo"]


class DemoResponse(BaseModel):
    household: HouseholdResponse
