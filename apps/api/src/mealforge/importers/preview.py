from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db
from mealforge.households.authorization import authorize
from mealforge.households.schemas import Input
from mealforge.identity.routes import Auth, require_mutation
from mealforge.importers.jsonld import PARSER_VERSION, parse_own_jsonld

router = APIRouter(
    prefix="/api/v1/households/{household_id}/recipe-imports",
    tags=["recipe-imports"],
    responses=PROBLEM_RESPONSES,
)


class PreviewInput(Input):
    document: str = Field(min_length=1, max_length=12288)
    rights_attestation: Literal["i_am_author"]


class PreviewIngredient(BaseModel):
    literal_text: str
    amount: None = None
    unit: Literal["unknown"] = "unknown"
    weight_state: Literal["unknown"] = "unknown"


class PreviewStep(BaseModel):
    text: str
    section_path: list[str]


class PreviewResponse(BaseModel):
    title: str
    ingredients: list[PreviewIngredient]
    instructions: list[PreviewStep]
    recipe_yield_raw: list[str]
    source_sha256: str
    parser_version: Literal["jsonld-preview-v1"] = PARSER_VERSION
    ignored_source_fields: list[str]
    source_mode: Literal["user_supplied_jsonld"] = "user_supplied_jsonld"
    rights_mode: Literal["private_user_content"] = "private_user_content"
    license: None = None
    nutrition_status: Literal["unknown"] = "unknown"
    allergen_status: Literal["unknown"] = "unknown"
    status: Literal["draft_requires_review"] = "draft_requires_review"
    planner_eligible: Literal[False] = False
    persisted: Literal[False] = False


@router.post("/preview", response_model=PreviewResponse)
def preview(
    household_id: UUID,
    payload: PreviewInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> PreviewResponse:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)
    try:
        parsed = parse_own_jsonld(payload.document)
    except ValueError:
        raise ApiError(
            422,
            "JSONLD_INVALID",
            "Nieprawidłowy lub nieobsługiwany dokument "
            "własnego przepisu. Podaj jeden przepis z tytułem, składnikami "
            "i instrukcjami; użyj samego JSON, bez HTML.",
        ) from None
    return PreviewResponse(
        title=parsed.title,
        ingredients=[PreviewIngredient(literal_text=text) for text in parsed.ingredients],
        instructions=[
            PreviewStep(text=step.text, section_path=list(step.section_path))
            for step in parsed.instructions
        ],
        recipe_yield_raw=list(parsed.recipe_yield_raw),
        source_sha256=parsed.source_sha256,
        ignored_source_fields=list(parsed.ignored_source_fields),
    )
