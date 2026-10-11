from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from mealforge.households.schemas import Input


class RecipeLinkInput(Input):
    user_title: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=1, max_length=2048)
    own_note: str | None = Field(default=None, max_length=2000)
    own_contribution_attestation: Literal["i_am_author_of_label_and_note"]

    @field_validator("user_title")
    @classmethod
    def valid_title(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Nieprawidłowa własna nazwa linku.")
        return value.strip()

    @field_validator("own_note")
    @classmethod
    def valid_note(cls, value: str | None) -> str | None:
        if value is not None and any(
            (ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in value
        ):
            raise ValueError("Nieprawidłowa własna notatka.")
        return value


class RecipeLinkSummary(BaseModel):
    id: UUID
    household_id: UUID
    user_title: str
    source_url: str
    host: str
    source_id: str | None
    source_registry_checked_at: str
    status: Literal["link_only"]
    version: Literal[1]
    planner_eligible: Literal[False]
    license: None
    automatic_fetch_enabled: Literal[False]
    nutrition_status: Literal["unknown"]
    allergen_status: Literal["unknown"]
    created_at: str


class RecipeLinkDetail(RecipeLinkSummary):
    canonical_url: str
    own_note: str | None
    own_contribution_attestation: Literal["i_am_author_of_label_and_note"]
    actor_user_id: UUID


class RecipeLinksResponse(BaseModel):
    recipe_links: list[RecipeLinkSummary]
    next_cursor: UUID | None
