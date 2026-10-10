import re
from datetime import date, time
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
    field_validator,
    model_validator,
)


def exact_amount(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Podaj liczbę całkowitą lub dokładny zapis dziesiętny.")
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,3})?", str(value)):
        raise ValueError("Nieprawidłowa wartość dziesiętna.")
    return Decimal(value)


AMOUNT_SCHEMA = {
    "anyOf": [
        {"type": "integer", "minimum": 0, "maximum": 999999},
        {"type": "string", "pattern": r"^(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,3})?$(?![\s\S])"},
    ]
}
Amount = Annotated[
    Decimal,
    BeforeValidator(exact_amount),
    Field(ge=0, le=Decimal("999999.999")),
    WithJsonSchema(AMOUNT_SCHEMA),
]
Energy = Annotated[
    Amount,
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "integer", "minimum": 1, "maximum": 999999},
                {
                    "type": "string",
                    "pattern": r"^(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,3})?$(?![\s\S])",
                    "not": {"pattern": r"^0(?:\.0{1,3})?$(?![\s\S])"},
                },
            ]
        }
    ),
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HouseholdInput(Input):
    name: str = Field(min_length=1, max_length=80)
    timezone: str = Field(default="Europe/Warsaw", max_length=64)
    currency: Literal["PLN"] = "PLN"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Nieprawidłowa nazwa.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Nieprawidłowa strefa czasowa.") from None
        return value


class MemberInput(Input):
    display_name: str = Field(min_length=1, max_length=80)
    is_guest: bool = False
    role: Literal["editor", "viewer"] = "viewer"

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return HouseholdInput.clean_name(value)


class TargetInput(Input):
    expected_version: int = Field(ge=0, strict=True)
    kcal_target: Energy | None
    protein_target_g: Amount | None
    carbs_target_g: Amount | None
    fat_target_g: Amount | None
    goal_type: Literal["cut", "recomposition", "maintenance", "bulk", "custom"]
    valid_from: date

    @field_validator("kcal_target")
    @classmethod
    def positive_energy(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Cel energii musi być dodatni.")
        return value


def exact_share(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Nieprawidłowy udział.")
    if not re.fullmatch(r"(?:0|1)(?:\.[0-9]{1,5})?", str(value)):
        raise ValueError("Nieprawidłowy udział.")
    result = Decimal(value)
    if result > 1:
        raise ValueError("Nieprawidłowy udział.")
    return result


class SlotInput(Input):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=80)
    default_time: time | None = None
    default_share: (
        Annotated[
            Decimal,
            BeforeValidator(exact_share),
            WithJsonSchema(
                {
                    "anyOf": [
                        {"type": "integer", "minimum": 0, "maximum": 1},
                        {
                            "type": "string",
                            "pattern": r"^(?:0(?:\.[0-9]{1,5})?|1(?:\.0{1,5})?)$(?![\s\S])",
                        },
                    ]
                }
            ),
        ]
        | None
    ) = None
    repeat_weekly: bool

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return HouseholdInput.clean_name(value)

    @field_validator("default_time", mode="before")
    @classmethod
    def local_time(cls, value: object) -> object:
        if value is not None and (
            not isinstance(value, str)
            or not re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", value)
        ):
            raise ValueError("Podaj lokalną godzinę.")
        return value


class SlotsInput(Input):
    expected_version: int = Field(ge=1, strict=True)
    slots: list[SlotInput] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def valid_set(self) -> "SlotsInput":
        ids = [slot.id for slot in self.slots if slot.id]
        if len(ids) != len(set(ids)):
            raise ValueError("Powtórzony identyfikator posiłku.")
        if sum((slot.default_share or Decimal(0)) for slot in self.slots) > 1:
            raise ValueError("Suma udziałów przekracza całość.")
        return self


class HouseholdResponse(BaseModel):
    id: str
    name: str
    timezone: str
    currency: str
    role: str


class HouseholdsResponse(BaseModel):
    households: list[HouseholdResponse]


class WarningResponse(BaseModel):
    code: str
    message: str


class TargetResponse(BaseModel):
    id: str
    version: int
    kcal_target: str | None
    protein_target_g: str | None
    carbs_target_g: str | None
    fat_target_g: str | None
    goal_type: str
    valid_from: str
    created_at: str
    warnings: list[WarningResponse]


class HistoryResponse(BaseModel):
    history: list[TargetResponse]


class MemberResponse(BaseModel):
    id: str
    display_name: str
    role: str
    is_guest: bool
    user_id: str | None
    nutrition_target: TargetResponse | None
    version: int


class MembersResponse(BaseModel):
    members: list[MemberResponse]


class SlotResponse(BaseModel):
    id: str
    name: str
    ordering: int
    default_time: str | None
    default_share: str | None
    repeat_weekly: bool


class SlotsResponse(BaseModel):
    version: int
    slots: list[SlotResponse]
