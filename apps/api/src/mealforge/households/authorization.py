from typing import TypedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mealforge.core.api import ApiError
from mealforge.households.models import Household, HouseholdMember
from mealforge.identity.routes import Authenticated


class Capabilities(TypedDict):
    can_edit: bool
    can_manage_access: bool


def capabilities(household: Household, member: HouseholdMember) -> Capabilities:
    enabled = (
        member.active
        and member.access_enabled
        and not member.is_guest
        and member.user_id is not None
    )
    return {
        "can_edit": enabled and member.role in {"owner", "editor"},
        "can_manage_access": enabled
        and member.role == "owner"
        and member.user_id == household.owner_user_id,
    }


def authorize(
    db: Session,
    auth: Authenticated,
    household_id: UUID,
    *,
    write: bool = False,
    owner: bool = False,
) -> HouseholdMember:
    # All private commands, reads, replays and access changes lock the household first.
    # Acceptance takes this same lock before invitation/member locks, preventing stale grants.
    household = db.scalar(
        select(Household)
        .where(Household.id == household_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if household is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")
    member = db.scalar(
        select(HouseholdMember)
        .where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == auth.user.id,
            HouseholdMember.active.is_(True),
            HouseholdMember.access_enabled.is_(True),
            HouseholdMember.is_guest.is_(False),
        )
        .execution_options(populate_existing=True)
    )
    if member is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")
    permissions = capabilities(household, member)
    if (owner and not permissions["can_manage_access"]) or (write and not permissions["can_edit"]):
        raise ApiError(403, "EDIT_FORBIDDEN", "Nie masz uprawnień do zmiany danych.")
    return member
