from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, audit, mutate
from mealforge.households.authorization import authorize
from mealforge.identity.routes import Auth, require_mutation
from mealforge.recipes.models import Recipe, RecipeVersion
from mealforge.recipes.schemas import (
    RecipeDetail,
    RecipeHistoryResponse,
    RecipeInput,
    RecipeSnapshot,
    RecipesResponse,
    RecipeUpdateInput,
)
from mealforge.recipes.service import append_version, new_recipe, snapshot

router = APIRouter(
    prefix="/api/v1/households/{household_id}/recipes",
    tags=["recipes"],
    responses=PROBLEM_RESPONSES,
)


def scoped_recipe(db: Session, household: UUID, recipe: UUID) -> Recipe:
    row = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe, Recipe.household_id == household)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")
    return row


def current_version(db: Session, recipe: Recipe) -> RecipeVersion:
    version = db.scalar(
        select(RecipeVersion).where(
            RecipeVersion.recipe_id == recipe.id,
            RecipeVersion.household_id == recipe.household_id,
            RecipeVersion.version == recipe.current_version,
        )
    )
    assert version is not None
    return version


def detail(version: RecipeVersion) -> dict[str, Any]:
    result = RecipeSnapshot.model_validate(version.snapshot).model_dump(mode="json")
    return {
        **result,
        "id": str(version.recipe_id),
        "household_id": str(version.household_id),
        "version": version.version,
        "version_id": str(version.id),
        "created_at": version.created_at.isoformat(),
    }


def summary(version: RecipeVersion) -> dict[str, Any]:
    result = detail(version)
    return {
        key: result[key]
        for key in (
            "id",
            "household_id",
            "version",
            "title",
            "created_at",
            "status",
            "planner_eligible",
            "warnings",
        )
    }


@router.get("", response_model=RecipesResponse)
def list_recipes(
    household_id: UUID,
    db: Db,
    auth: Auth,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    after: UUID | None = None,
) -> dict[str, Any]:
    authorize(db, auth, household_id)
    query = (
        select(RecipeVersion)
        .join(
            Recipe,
            (Recipe.id == RecipeVersion.recipe_id)
            & (Recipe.household_id == RecipeVersion.household_id)
            & (Recipe.current_version == RecipeVersion.version),
        )
        .where(Recipe.household_id == household_id)
    )
    if after:
        query = query.where(Recipe.id > after)
    rows = db.scalars(query.order_by(Recipe.id).limit(limit + 1)).all()
    return {
        "recipes": [summary(row) for row in rows[:limit]],
        "next_cursor": str(rows[limit - 1].recipe_id) if len(rows) > limit else None,
    }


@router.post("", status_code=201, response_model=RecipeDetail)
def create_recipe(
    household_id: UUID,
    payload: RecipeInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)

    def operation() -> dict[str, Any]:
        version = new_recipe(
            db, household_id, auth.user.id, snapshot(payload, auth.user.display_name)
        )
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "recipe.created",
            "recipe",
            version.recipe_id,
            None,
            1,
        )
        return {"recipe_id": str(version.recipe_id), "version": 1}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "recipe.create",
        payload.model_dump(mode="json"),
        operation,
    )
    recipe = scoped_recipe(db, household_id, UUID(reference["recipe_id"]))
    return detail(version_at(db, recipe, reference["version"]))


def version_at(db: Session, recipe: Recipe, version_number: int) -> RecipeVersion:
    row = db.scalar(
        select(RecipeVersion).where(
            RecipeVersion.recipe_id == recipe.id,
            RecipeVersion.household_id == recipe.household_id,
            RecipeVersion.version == version_number,
        )
    )
    assert row is not None
    return row


@router.get("/{recipe_id}", response_model=RecipeDetail)
def get_recipe(household_id: UUID, recipe_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id)
    return detail(current_version(db, scoped_recipe(db, household_id, recipe_id)))


@router.put("/{recipe_id}", response_model=RecipeDetail)
def update_recipe(
    household_id: UUID,
    recipe_id: UUID,
    payload: RecipeUpdateInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)
    recipe = scoped_recipe(db, household_id, recipe_id)

    def operation() -> dict[str, Any]:
        if recipe.current_version != payload.expected_version:
            raise ApiError(409, "VERSION_CONFLICT", "Przepis został już zmieniony. Odśwież dane.")
        previous = current_version(db, recipe)
        recipe.current_version += 1
        version = append_version(
            db, recipe, auth.user.id, snapshot(payload, auth.user.display_name, previous)
        )
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "recipe.updated",
            "recipe",
            recipe.id,
            payload.expected_version,
            version.version,
        )
        return {"recipe_id": str(recipe.id), "version": version.version}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "recipe.update",
        {"recipe_id": str(recipe_id), **payload.model_dump(mode="json")},
        operation,
    )
    return detail(version_at(db, recipe, reference["version"]))


@router.get("/{recipe_id}/history", response_model=RecipeHistoryResponse)
def recipe_history(
    household_id: UUID,
    recipe_id: UUID,
    db: Db,
    auth: Auth,
    limit: Annotated[int, Query(ge=1, le=5)] = 5,
    before_version: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, Any]:
    authorize(db, auth, household_id)
    scoped_recipe(db, household_id, recipe_id)
    query = select(RecipeVersion).where(
        RecipeVersion.recipe_id == recipe_id, RecipeVersion.household_id == household_id
    )
    if before_version is not None:
        query = query.where(RecipeVersion.version < before_version)
    rows = db.scalars(query.order_by(RecipeVersion.version.desc()).limit(limit + 1)).all()
    return {
        "history": [detail(row) for row in rows[:limit]],
        "next_before_version": rows[limit - 1].version if len(rows) > limit else None,
    }
