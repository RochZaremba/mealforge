from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, audit, mutate, now
from mealforge.households.authorization import authorize, capabilities
from mealforge.households.models import Household, HouseholdMember, MealSlotPreset, NutritionProfile
from mealforge.households.schemas import (
    HistoryResponse,
    HouseholdInput,
    HouseholdResponse,
    HouseholdsResponse,
    MemberInput,
    MemberResponse,
    MembersResponse,
    SlotsInput,
    SlotsResponse,
    TargetInput,
    TargetResponse,
)
from mealforge.identity.routes import Auth, require_mutation
from mealforge.seed import MEAL_SLOT_DEFINITIONS

router = APIRouter(prefix="/api/v1/households", tags=["households"], responses=PROBLEM_RESPONSES)


def household_dto(household: Household, member: HouseholdMember) -> dict[str, Any]:
    return {
        "id": str(household.id),
        "name": household.name,
        "timezone": household.timezone,
        "currency": household.currency,
        "role": member.role,
        "capabilities": capabilities(household, member),
    }


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def target_dto(profile: NutritionProfile) -> dict[str, Any]:
    values = (
        profile.kcal_target,
        profile.protein_target_g,
        profile.carbs_target_g,
        profile.fat_target_g,
    )
    warnings = []
    if all(value is not None for value in values):
        kcal, protein, carbs, fat = values
        assert kcal is not None and protein is not None and carbs is not None and fat is not None
        if abs(4 * protein + 4 * carbs + 9 * fat - kcal) > Decimal("0.05") * kcal:
            warnings.append(
                {
                    "code": "ENERGY_MACRO_MISMATCH",
                    "message": "Kalorie i przybliżona energia z makro różnią się o ponad 5%. "
                    "Cele pozostają bez zmian.",
                }
            )
    return {
        "id": str(profile.id),
        "version": profile.version,
        "kcal_target": decimal_text(profile.kcal_target),
        "protein_target_g": decimal_text(profile.protein_target_g),
        "carbs_target_g": decimal_text(profile.carbs_target_g),
        "fat_target_g": decimal_text(profile.fat_target_g),
        "goal_type": profile.goal_type,
        "valid_from": profile.valid_from.isoformat(),
        "created_at": profile.created_at.isoformat(),
        "warnings": warnings,
    }


def member_dto(db: Session, member: HouseholdMember) -> dict[str, Any]:
    latest = db.scalar(
        select(NutritionProfile)
        .where(
            NutritionProfile.member_id == member.id,
            NutritionProfile.household_id == member.household_id,
        )
        .order_by(NutritionProfile.version.desc())
        .limit(1)
    )
    return {
        "id": str(member.id),
        "display_name": member.display_name,
        "role": member.role,
        "is_guest": member.is_guest,
        "user_id": str(member.user_id) if member.user_id else None,
        "nutrition_target": target_dto(latest) if latest else None,
        "version": member.target_revision,
        "access_enabled": member.access_enabled,
        "access_version": member.access_version,
    }


def scoped_member(
    db: Session, household_id: UUID, member_id: UUID, *, lock: bool = False
) -> HouseholdMember:
    query = select(HouseholdMember).where(
        HouseholdMember.household_id == household_id,
        HouseholdMember.id == member_id,
        HouseholdMember.active.is_(True),
    )
    member = db.scalar(query.with_for_update() if lock else query)
    if member is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")
    return member


def slots_dto(db: Session, household: Household) -> dict[str, Any]:
    rows = db.scalars(
        select(MealSlotPreset)
        .where(MealSlotPreset.household_id == household.id, MealSlotPreset.active.is_(True))
        .order_by(MealSlotPreset.ordering)
    ).all()
    return {
        "version": household.slot_revision,
        "slots": [
            {
                "id": str(slot.id),
                "name": slot.name,
                "ordering": slot.ordering,
                "default_time": slot.default_time.isoformat() if slot.default_time else None,
                "default_share": decimal_text(slot.default_share),
                "repeat_weekly": slot.repeat_weekly,
            }
            for slot in rows
        ],
    }


@router.get("", response_model=HouseholdsResponse)
def list_households(db: Db, auth: Auth) -> dict[str, Any]:
    rows = db.execute(
        select(Household, HouseholdMember)
        .join(HouseholdMember, HouseholdMember.household_id == Household.id)
        .where(
            HouseholdMember.user_id == auth.user.id,
            HouseholdMember.active.is_(True),
            HouseholdMember.access_enabled.is_(True),
            HouseholdMember.is_guest.is_(False),
        )
        .order_by(Household.created_at)
    ).all()
    # Recheck under the same per-household lock as revocation, including list results.
    result = []
    for household, _ in sorted(rows, key=lambda row: str(row[0].id)):
        try:
            membership = authorize(db, auth, household.id)
        except ApiError as error:
            if error.status == 404:
                continue
            raise
        result.append(household_dto(household, membership))
    return {"households": result}


@router.post("", status_code=201, response_model=HouseholdResponse)
def create_household(
    payload: HouseholdInput, request: Request, db: Db, auth: Auth, settings: Configuration
) -> dict[str, Any]:
    require_mutation(request, settings, auth)

    def operation() -> dict[str, Any]:
        household = Household(
            name=payload.name,
            owner_user_id=auth.user.id,
            timezone=payload.timezone,
            currency=payload.currency,
            slot_revision=1,
            created_at=now(),
        )
        db.add(household)
        db.flush()
        member = HouseholdMember(
            household_id=household.id,
            user_id=auth.user.id,
            display_name=auth.user.display_name,
            role="owner",
            is_guest=False,
            active=True,
            target_revision=0,
        )
        db.add(member)
        db.flush()
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
        audit(
            db, request, auth.user.id, household.id, "household.created", "household", household.id
        )
        return household_dto(household, member)

    def replay_authorize(result: dict[str, Any]) -> None:
        membership = authorize(db, auth, UUID(result["id"]), write=True)
        result["role"] = membership.role
        household = db.get(Household, UUID(result["id"]))
        assert household is not None
        result["capabilities"] = capabilities(household, membership)

    return mutate(
        db,
        request,
        auth.user.id,
        "user",
        "household.create",
        payload.model_dump(mode="json"),
        operation,
        replay_authorize,
    )


@router.get("/{household_id}", response_model=HouseholdResponse)
def get_household(household_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    member = authorize(db, auth, household_id)
    household = db.get(Household, household_id)
    assert household is not None
    return household_dto(household, member)


@router.get("/{household_id}/members", response_model=MembersResponse)
def list_members(household_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id)
    members = db.scalars(
        select(HouseholdMember)
        .where(HouseholdMember.household_id == household_id, HouseholdMember.active.is_(True))
        .order_by(HouseholdMember.id)
    ).all()
    return {"members": [member_dto(db, member) for member in members]}


@router.post("/{household_id}/members", status_code=201, response_model=MemberResponse)
def create_member(
    household_id: UUID,
    payload: MemberInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)

    def operation() -> dict[str, Any]:
        member = HouseholdMember(
            household_id=household_id,
            user_id=None,
            display_name=payload.display_name,
            role=payload.role,
            is_guest=payload.is_guest,
            active=True,
            target_revision=0,
        )
        db.add(member)
        db.flush()
        audit(db, request, auth.user.id, household_id, "member.created", "member", member.id)
        return member_dto(db, member)

    return mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "member.create",
        payload.model_dump(mode="json"),
        operation,
    )


@router.put("/{household_id}/members/{member_id}/nutrition-target", response_model=TargetResponse)
def set_target(
    household_id: UUID,
    member_id: UUID,
    payload: TargetInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)
    scoped_member(db, household_id, member_id)

    household = db.get(Household, household_id)
    assert household is not None
    if payload.valid_from > now().astimezone(ZoneInfo(household.timezone)).date():
        raise ApiError(
            422,
            "TARGET_DATE_INVALID",
            "W tym etapie cel może obowiązywać od dziś lub wcześniejszej daty.",
        )

    def operation() -> dict[str, Any]:
        member = scoped_member(db, household_id, member_id, lock=True)
        if member.target_revision != payload.expected_version:
            raise ApiError(
                409, "VERSION_CONFLICT", "Dane zostały zmienione. Odśwież widok i spróbuj ponownie."
            )
        previous = db.scalar(
            select(NutritionProfile)
            .where(
                NutritionProfile.member_id == member_id,
                NutritionProfile.household_id == household_id,
            )
            .order_by(NutritionProfile.version.desc())
            .limit(1)
        )
        if previous and payload.valid_from < previous.valid_from:
            raise ApiError(
                422,
                "TARGET_DATE_INVALID",
                "Nowa wersja celu nie może obowiązywać przed poprzednią.",
            )
        member.target_revision += 1
        profile = NutritionProfile(
            household_id=household_id,
            member_id=member.id,
            version=member.target_revision,
            kcal_target=payload.kcal_target,
            protein_target_g=payload.protein_target_g,
            carbs_target_g=payload.carbs_target_g,
            fat_target_g=payload.fat_target_g,
            goal_type=payload.goal_type,
            source="user_set",
            valid_from=payload.valid_from,
            created_at=now(),
            actor_user_id=auth.user.id,
        )
        db.add(profile)
        db.flush()
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "nutrition_target.created",
            "member",
            member.id,
            payload.expected_version,
            member.target_revision,
        )
        return target_dto(profile)

    return mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        f"target.set:{member_id}",
        payload.model_dump(mode="json"),
        operation,
    )


@router.get(
    "/{household_id}/members/{member_id}/nutrition-target/history", response_model=HistoryResponse
)
def target_history(household_id: UUID, member_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id)
    scoped_member(db, household_id, member_id)
    rows = db.scalars(
        select(NutritionProfile)
        .where(
            NutritionProfile.household_id == household_id, NutritionProfile.member_id == member_id
        )
        .order_by(NutritionProfile.version.desc())
    ).all()
    return {"history": [target_dto(profile) for profile in rows]}


@router.get("/{household_id}/meal-slot-presets", response_model=SlotsResponse)
def get_slots(household_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id)
    household = db.get(Household, household_id)
    assert household is not None
    return slots_dto(db, household)


@router.put("/{household_id}/meal-slot-presets", response_model=SlotsResponse)
def set_slots(
    household_id: UUID,
    payload: SlotsInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, write=True)

    def operation() -> dict[str, Any]:
        household = db.scalar(
            select(Household).where(Household.id == household_id).with_for_update()
        )
        assert household is not None
        if household.slot_revision != payload.expected_version:
            raise ApiError(
                409,
                "VERSION_CONFLICT",
                "Posiłki zostały zmienione. Odśwież widok i spróbuj ponownie.",
            )
        existing = {
            slot.id: slot
            for slot in db.scalars(
                select(MealSlotPreset).where(MealSlotPreset.household_id == household_id)
            ).all()
        }
        if any(slot.id and slot.id not in existing for slot in payload.slots):
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono posiłku.")
        for slot in existing.values():
            slot.active = False
        for ordering, item in enumerate(payload.slots):
            slot = existing[item.id] if item.id else MealSlotPreset(household_id=household_id)
            slot.name, slot.ordering = item.name, ordering
            slot.default_time, slot.default_share = item.default_time, item.default_share
            slot.repeat_weekly, slot.active = item.repeat_weekly, True
            db.add(slot)
        household.slot_revision += 1
        db.flush()
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "meal_slots.updated",
            "household",
            household_id,
            payload.expected_version,
            household.slot_revision,
        )
        return slots_dto(db, household)

    return mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "slots.replace",
        payload.model_dump(mode="json"),
        operation,
    )
