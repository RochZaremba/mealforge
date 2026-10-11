from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import ValidationError
from sqlalchemy import select, text

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, audit, mutate, now
from mealforge.households.authorization import authorize
from mealforge.identity.routes import Auth, require_mutation
from mealforge.importers.jsonld import PARSER_VERSION, parse_own_jsonld
from mealforge.importers.preview import PreviewInput
from mealforge.recipes.models import RecipeVersion
from mealforge.recipes.routes import detail, scoped_recipe, version_at
from mealforge.recipes.schemas import RecipeDetail, RecipeInput
from mealforge.recipes.service import new_recipe, snapshot, validated_snapshot

router = APIRouter(
    prefix="/api/v1/households/{household_id}/recipe-imports",
    tags=["recipe-imports"],
    responses=PROBLEM_RESPONSES,
)


@router.post("", status_code=201, response_model=RecipeDetail)
def save_import(
    household_id: UUID,
    payload: PreviewInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)

    def operation() -> dict[str, Any]:
        try:
            parsed = parse_own_jsonld(payload.document)
        except ValueError:
            raise ApiError(
                422,
                "JSONLD_INVALID",
                "Nieprawidłowy lub nieobsługiwany dokument własnego przepisu. "
                "Podaj jeden przepis z tytułem, składnikami i instrukcjami; "
                "użyj samego JSON, bez HTML.",
            ) from None
        duplicate = db.scalar(
            select(RecipeVersion.id).where(
                RecipeVersion.household_id == household_id,
                RecipeVersion.version == 1,
                text(
                    "(recipe_versions.snapshot #>> "
                    "'{provenance,import_origin,source_sha256}'::text[]) = :source_sha"
                ).bindparams(source_sha=parsed.source_sha256),
            )
        )
        if duplicate:
            raise ApiError(
                409,
                "JSONLD_ALREADY_IMPORTED",
                "Ten sam dokument został już zapisany w gospodarstwie.",
            )
        try:
            recipe_input = RecipeInput.model_validate(
                {
                    "title": parsed.title,
                    "ingredients": [
                        {"name": item, "amount": None, "unit": "unknown", "weight_state": "unknown"}
                        for item in parsed.ingredients
                    ],
                    "instructions": [step.text for step in parsed.instructions],
                    "rights_attestation": payload.rights_attestation,
                }
            )
        except ValidationError:
            raise ApiError(
                422,
                "JSONLD_CATALOGUE_LIMIT",
                "Dokument można podejrzeć, lecz zapis wymaga nazwy składnika do 160 znaków, "
                "tytułu do 160 i kroków do 500 znaków, bez niedozwolonych znaków. "
                "Skróć własny dokument; niczego nie obcięto ani nie zapisano.",
            ) from None
        data = snapshot(recipe_input, auth.user.display_name)
        # Keep accepted source literals exactly; the manual editor's trimming is not an import.
        data["title"] = parsed.title
        data["instructions"] = [step.text for step in parsed.instructions]
        for item, literal in zip(data["ingredients"], parsed.ingredients, strict=True):
            item["name"] = literal
        data["provenance"]["source_mode"] = "user_supplied_jsonld"
        data["provenance"]["import_origin"] = {
            "source_sha256": parsed.source_sha256,
            "parser_version": PARSER_VERSION,
            "actor_user_id": str(auth.user.id),
            "imported_at": now().isoformat(),
            "ingredients": list(parsed.ingredients),
            "instructions": [
                {"text": step.text, "section_path": list(step.section_path)}
                for step in parsed.instructions
            ],
            "recipe_yield_raw": list(parsed.recipe_yield_raw),
            "ignored_source_fields": list(parsed.ignored_source_fields),
        }
        version = new_recipe(db, household_id, auth.user.id, validated_snapshot(data))
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "recipe.jsonld_imported",
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
        "recipe.jsonld_import",
        payload.model_dump(mode="json"),
        operation,
    )
    recipe = scoped_recipe(db, household_id, UUID(reference["recipe_id"]))
    return detail(version_at(db, recipe, reference["version"]))
