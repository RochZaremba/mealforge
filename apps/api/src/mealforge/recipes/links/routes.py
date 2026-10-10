from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, audit, mutate, now
from mealforge.households.authorization import authorize
from mealforge.identity.routes import Auth, require_mutation
from mealforge.importers.url_policy import classify_source, validate_recipe_url
from mealforge.recipes.links.models import RecipeLink
from mealforge.recipes.links.registry import load_source_registry
from mealforge.recipes.links.schemas import RecipeLinkDetail, RecipeLinkInput, RecipeLinksResponse

router = APIRouter(
    prefix="/api/v1/households/{household_id}/recipe-links",
    tags=["recipe-links"],
    responses=PROBLEM_RESPONSES,
)


def scoped_link(db: Session, household: UUID, link_id: UUID) -> RecipeLink:
    row = db.scalar(
        select(RecipeLink).where(RecipeLink.id == link_id, RecipeLink.household_id == household)
    )
    if row is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")
    return row


def detail(row: RecipeLink) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "household_id": str(row.household_id),
        "user_title": row.user_title,
        "source_url": row.source_url,
        "canonical_url": row.canonical_url,
        "host": row.host,
        "source_id": row.source_id,
        "source_registry_checked_at": row.source_registry_checked_at.isoformat(),
        "own_note": row.own_note,
        "own_contribution_attestation": row.own_contribution_attestation,
        "actor_user_id": str(row.actor_user_id),
        "status": row.status,
        "version": row.version,
        "planner_eligible": row.planner_eligible,
        "license": row.license,
        "automatic_fetch_enabled": row.automatic_fetch_enabled,
        "nutrition_status": "unknown",
        "allergen_status": "unknown",
        "created_at": row.created_at.isoformat(),
    }


def summary(row: RecipeLink) -> dict[str, Any]:
    result = detail(row)
    for key in ("canonical_url", "own_note", "own_contribution_attestation", "actor_user_id"):
        result.pop(key)
    return result


@router.get("", response_model=RecipeLinksResponse)
def list_links(
    household_id: UUID,
    db: Db,
    auth: Auth,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    after: UUID | None = None,
) -> dict[str, Any]:
    authorize(db, auth, household_id)
    query = select(RecipeLink).where(RecipeLink.household_id == household_id)
    if after:
        query = query.where(RecipeLink.id > after)
    rows = db.scalars(query.order_by(RecipeLink.id).limit(limit + 1)).all()
    return {
        "recipe_links": [summary(row) for row in rows[:limit]],
        "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
    }


@router.post("", status_code=201, response_model=RecipeLinkDetail)
def create_link(
    household_id: UUID,
    payload: RecipeLinkInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)
    try:
        validated = validate_recipe_url(payload.source_url)
    except ValueError:
        raise ApiError(422, "URL_INVALID", "Podaj poprawny publiczny adres HTTPS.") from None

    def operation() -> dict[str, Any]:
        duplicate = db.scalar(
            select(RecipeLink.id).where(
                RecipeLink.household_id == household_id,
                RecipeLink.canonical_url == validated.canonical_url,
            )
        )
        if duplicate:
            raise ApiError(409, "RECIPE_LINK_EXISTS", "Ten link jest już zapisany w gospodarstwie.")
        registry = load_source_registry()
        row = RecipeLink(
            household_id=household_id,
            actor_user_id=auth.user.id,
            created_at=now(),
            user_title=payload.user_title,
            own_note=payload.own_note,
            own_contribution_attestation=payload.own_contribution_attestation,
            source_url=validated.source_url,
            canonical_url=validated.canonical_url,
            host=validated.host,
            source_id=classify_source(validated.host, registry),
            source_registry_checked_at=date.fromisoformat(registry["checked_at"]),
        )
        db.add(row)
        db.flush()
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "recipe_link.created",
            "recipe_link",
            row.id,
            None,
            1,
        )
        return {"link_id": str(row.id)}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "recipe_link.create",
        payload.model_dump(mode="json"),
        operation,
    )
    return detail(scoped_link(db, household_id, UUID(reference["link_id"])))


@router.get("/{link_id}", response_model=RecipeLinkDetail)
def get_link(household_id: UUID, link_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id)
    return detail(scoped_link(db, household_id, link_id))
