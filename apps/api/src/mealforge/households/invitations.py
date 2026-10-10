import hmac
import re
import secrets
from datetime import timedelta
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import Field, StrictBool
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, audit, mutate, now
from mealforge.core.config import Settings
from mealforge.households.authorization import authorize
from mealforge.households.models import Household, HouseholdInvitation, HouseholdMember
from mealforge.households.routes import household_dto, member_dto, scoped_member
from mealforge.households.schemas import HouseholdResponse, Input, MemberResponse
from mealforge.identity.routes import Auth, require_mutation, secret

router = APIRouter(prefix="/api/v1", tags=["invitations"], responses=PROBLEM_RESPONSES)


class InvitationInput(Input):
    role: Literal["editor", "viewer"]
    member_id: UUID | None = None


class VersionInput(Input):
    expected_version: int = Field(ge=1, strict=True)


class AccessInput(Input):
    expected_version: int = Field(ge=0, strict=True)
    role: Literal["editor", "viewer"]
    access_enabled: StrictBool


class AcceptInput(Input):
    token: str = Field(
        min_length=64, max_length=64, pattern=re.compile(r"^[0-9a-f]{64}$(?![\s\S])")
    )


class InvitationResponse(Input):
    id: str
    role: Literal["editor", "viewer"]
    member_id: str | None
    expires_at: str
    status: Literal["pending", "accepted", "revoked", "expired"]
    version: int


class CreatedInvitationResponse(InvitationResponse):
    token: str


class InvitationsResponse(Input):
    invitations: list[InvitationResponse]


class AcceptedInvitationResponse(Input):
    household: HouseholdResponse
    member: MemberResponse


def invitation_dto(invitation: HouseholdInvitation) -> dict[str, Any]:
    status = "pending"
    if invitation.accepted_at:
        status = "accepted"
    elif invitation.revoked_at:
        status = "revoked"
    elif invitation.expires_at <= now():
        status = "expired"
    return {
        "id": str(invitation.id),
        "role": invitation.role,
        "member_id": str(invitation.member_id) if invitation.member_id else None,
        "expires_at": invitation.expires_at.isoformat(),
        "status": status,
        "version": invitation.version,
    }


def derive_token(invitation: HouseholdInvitation, settings: Settings) -> str:
    message = f"mealforge:invitation:v1:{invitation.id}:{invitation.private_nonce}".encode()
    return hmac.new(secret(settings), message, "sha256").hexdigest()


def verified_token(invitation: HouseholdInvitation, settings: Settings) -> str:
    token = derive_token(invitation, settings)
    if not hmac.compare_digest(sha256(token.encode()).hexdigest(), invitation.token_hash):
        raise ApiError(
            409,
            "INVITATION_SECRET_CHANGED",
            "Zaproszenie straciło ważność po zmianie zabezpieczeń. Utwórz nowe.",
        )
    return token


def scoped_invitation(db: Session, hid: UUID, iid: UUID) -> HouseholdInvitation:
    record = db.scalar(
        select(HouseholdInvitation)
        .where(HouseholdInvitation.id == iid, HouseholdInvitation.household_id == hid)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zaproszenia.")
    return record


@router.post(
    "/households/{household_id}/invite", status_code=201, response_model=CreatedInvitationResponse
)
def create_invitation(
    household_id: UUID,
    payload: InvitationInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, owner=True)

    def operation() -> dict[str, Any]:
        if payload.member_id:
            member = scoped_member(db, household_id, payload.member_id, lock=True)
            if member.is_guest:
                raise ApiError(
                    422,
                    "GUEST_LOGIN_FORBIDDEN",
                    "Profil gościa nie może otrzymać dostępu do konta.",
                )
            if member.user_id is not None:
                raise ApiError(409, "MEMBER_ALREADY_LINKED", "Ta osoba ma już powiązane konto.")
        instant = now()
        invitation = HouseholdInvitation(
            id=uuid4(),
            household_id=household_id,
            member_id=payload.member_id,
            role=payload.role,
            private_nonce=secrets.token_hex(32),
            created_at=instant,
            expires_at=instant + timedelta(hours=24),
            version=1,
        )
        invitation.token_hash = sha256(derive_token(invitation, settings).encode()).hexdigest()
        db.add(invitation)
        db.flush()
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "invitation.created",
            "invitation",
            invitation.id,
            None,
            1,
        )
        # References only: raw code and nonce never enter idempotency JSON or audit.
        return {"invitation_id": str(invitation.id)}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        "invitation.create",
        payload.model_dump(mode="json"),
        operation,
    )
    invitation = scoped_invitation(db, household_id, UUID(reference["invitation_id"]))
    return invitation_dto(invitation) | {"token": verified_token(invitation, settings)}


@router.get("/households/{household_id}/invitations", response_model=InvitationsResponse)
def list_invitations(household_id: UUID, db: Db, auth: Auth) -> dict[str, Any]:
    authorize(db, auth, household_id, owner=True)
    records = db.scalars(
        select(HouseholdInvitation)
        .where(HouseholdInvitation.household_id == household_id)
        .order_by(HouseholdInvitation.created_at.desc())
    ).all()
    return {"invitations": [invitation_dto(record) for record in records]}


@router.post(
    "/households/{household_id}/invitations/{invitation_id}/revoke",
    response_model=InvitationResponse,
)
def revoke_invitation(
    household_id: UUID,
    invitation_id: UUID,
    payload: VersionInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, owner=True)
    scoped_invitation(db, household_id, invitation_id)

    def operation() -> dict[str, Any]:
        record = scoped_invitation(db, household_id, invitation_id)
        if record.version != payload.expected_version:
            raise ApiError(409, "VERSION_CONFLICT", "Zaproszenie zostało zmienione. Odśwież widok.")
        if record.accepted_at:
            raise ApiError(409, "INVITATION_USED", "Zaproszenie zostało już przyjęte.")
        if record.revoked_at:
            raise ApiError(409, "INVITATION_UNAVAILABLE", "Zaproszenie zostało już cofnięte.")
        record.revoked_at, record.version = now(), record.version + 1
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "invitation.revoked",
            "invitation",
            record.id,
            payload.expected_version,
            record.version,
        )
        return {"invitation_id": str(record.id)}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        f"invitation.revoke:{invitation_id}",
        payload.model_dump(mode="json"),
        operation,
    )
    return invitation_dto(scoped_invitation(db, household_id, UUID(reference["invitation_id"])))


@router.post("/household-invitations/accept", response_model=AcceptedInvitationResponse)
def accept_invitation(
    payload: AcceptInput, request: Request, db: Db, auth: Auth, settings: Configuration
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    if not re.fullmatch(r"[0-9a-f]{64}", payload.token):
        raise ApiError(422, "INVITATION_INVALID", "Nieprawidłowy kod zaproszenia.")
    peek = db.execute(
        select(HouseholdInvitation.id, HouseholdInvitation.household_id).where(
            HouseholdInvitation.token_hash == sha256(payload.token.encode()).hexdigest()
        )
    ).one_or_none()
    if peek is None:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zaproszenia.")
    # Lock order is shared with authorization, revoke and access changes: household first.
    household = db.scalar(
        select(Household)
        .where(Household.id == peek.household_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert household is not None
    invitation = scoped_invitation(db, household.id, peek.id)
    verified_token(invitation, settings)

    def replay_authorize(result: dict[str, Any]) -> None:
        authorize(db, auth, UUID(result["household_id"]))
        member = scoped_member(db, UUID(result["household_id"]), UUID(result["member_id"]))
        if member.user_id != auth.user.id or not member.access_enabled:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Nie znaleziono zasobu.")

    def operation() -> dict[str, Any]:
        if invitation.accepted_at:
            raise ApiError(409, "INVITATION_USED", "Zaproszenie zostało już przyjęte.")
        if invitation.revoked_at or invitation.expires_at <= now():
            raise ApiError(
                410, "INVITATION_UNAVAILABLE", "Zaproszenie wygasło lub zostało cofnięte."
            )
        existing = db.scalar(
            select(HouseholdMember)
            .where(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id == auth.user.id,
            )
            .with_for_update()
        )
        if existing:
            raise ApiError(
                409, "ALREADY_A_MEMBER", "To konto jest już powiązane z osobą w tym gospodarstwie."
            )
        if invitation.member_id:
            member = scoped_member(db, household.id, invitation.member_id, lock=True)
            if member.is_guest:
                raise ApiError(
                    422,
                    "GUEST_LOGIN_FORBIDDEN",
                    "Profil gościa nie może otrzymać dostępu do konta.",
                )
            if member.user_id is not None:
                raise ApiError(409, "MEMBER_ALREADY_LINKED", "Ta osoba ma już powiązane konto.")
        else:
            member = HouseholdMember(
                household_id=household.id,
                display_name=auth.user.display_name,
                target_revision=0,
                active=True,
                is_guest=False,
                access_version=0,
            )
            db.add(member)
        member.user_id, member.role = auth.user.id, invitation.role
        member.access_enabled, member.access_version = True, member.access_version + 1
        invitation.accepted_at, invitation.accepted_by_user_id = now(), auth.user.id
        invitation.version += 1
        db.flush()
        audit(
            db,
            request,
            auth.user.id,
            household.id,
            "invitation.accepted",
            "invitation",
            invitation.id,
            invitation.version - 1,
            invitation.version,
        )
        audit(
            db,
            request,
            auth.user.id,
            household.id,
            "member.access_linked",
            "member",
            member.id,
            member.access_version - 1,
            member.access_version,
        )
        return {"household_id": str(household.id), "member_id": str(member.id)}

    reference = mutate(
        db,
        request,
        auth.user.id,
        f"invitation:{invitation.id}",
        "invitation.accept",
        payload.model_dump(mode="json"),
        operation,
        replay_authorize,
    )
    membership = authorize(db, auth, household.id)
    member = scoped_member(db, household.id, UUID(reference["member_id"]))
    return {"household": household_dto(household, membership), "member": member_dto(db, member)}


@router.put("/households/{household_id}/members/{member_id}/access", response_model=MemberResponse)
def change_access(
    household_id: UUID,
    member_id: UUID,
    payload: AccessInput,
    request: Request,
    db: Db,
    auth: Auth,
    settings: Configuration,
) -> dict[str, Any]:
    require_mutation(request, settings, auth)
    authorize(db, auth, household_id, owner=True)
    member = scoped_member(db, household_id, member_id, lock=True)
    household = db.get(Household, household_id)
    assert household is not None
    if member.user_id == household.owner_user_id:
        raise ApiError(
            409, "OWNER_ACCESS_PROTECTED", "Nie można odebrać ani zmienić dostępu właściciela."
        )

    def operation() -> dict[str, Any]:
        if member.access_version != payload.expected_version:
            raise ApiError(409, "VERSION_CONFLICT", "Dostęp został zmieniony. Odśwież widok.")
        if member.user_id is None or member.is_guest:
            raise ApiError(422, "MEMBER_NOT_LINKED", "Ta osoba nie ma powiązanego konta.")
        member.role, member.access_enabled = payload.role, payload.access_enabled
        member.access_version += 1
        audit(
            db,
            request,
            auth.user.id,
            household_id,
            "member.access_changed",
            "member",
            member.id,
            payload.expected_version,
            member.access_version,
        )
        return {"member_id": str(member.id)}

    reference = mutate(
        db,
        request,
        auth.user.id,
        str(household_id),
        f"member.access:{member_id}",
        payload.model_dump(mode="json"),
        operation,
    )
    return member_dto(db, scoped_member(db, household_id, UUID(reference["member_id"])))
