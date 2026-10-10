"""Independent one-use invitation acceptance against isolated PostgreSQL."""

import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Barrier
from time import monotonic, sleep
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.orm import Session

from mealforge.core.config import Settings
from mealforge.households.models import (
    AuditEvent,
    Household,
    HouseholdInvitation,
    HouseholdMember,
    IdempotencyRecord,
    NutritionProfile,
)
from mealforge.main import create_app

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:3000"
PASSWORD = "QA-invitations-password-2026!"
SECRET = "QA-invitation-domain-secret-" + "x" * 40
ClientFactory = Callable[[], TestClient]


@pytest.fixture
def invitation_settings(postgres_settings: Settings, migrated_engine: Engine) -> Settings:
    assert migrated_engine is not None
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr(SECRET),
        trusted_origins=(ORIGIN,),
        app_env="test",
    )


@pytest.fixture
def invitation_app(invitation_settings: Settings) -> FastAPI:
    return create_app(invitation_settings)


@pytest.fixture
def clients(invitation_app: FastAPI) -> Iterator[ClientFactory]:
    with ExitStack() as stack:
        yield lambda: stack.enter_context(TestClient(invitation_app))


def headers(client: TestClient, key: str | None = None) -> dict[str, str]:
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    return {
        "Origin": ORIGIN,
        "X-CSRF-Token": session.json()["csrf_token"],
        "Idempotency-Key": key or str(uuid4()),
    }


@dataclass
class Person:
    client: TestClient
    user_id: str
    email: str


def person(clients: ClientFactory) -> Person:
    client = clients()
    email = f"invite-{uuid4().hex}@example.invalid"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Osoba QA"},
        headers={"Origin": ORIGIN},
    )
    assert registered.status_code == 201
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert signed_in.status_code == 200
    return Person(client, signed_in.json()["user"]["id"], email)


@dataclass
class Home:
    owner: Person
    id: str
    owner_member_id: str
    resident_id: str


def home(clients: ClientFactory, *, guest: bool = False) -> Home:
    owner = person(clients)
    created = owner.client.post(
        "/api/v1/households", json={"name": "Dom QA"}, headers=headers(owner.client)
    )
    assert created.status_code == 201
    household_id = created.json()["id"]
    members = owner.client.get(f"/api/v1/households/{household_id}/members").json()["members"]
    owner_member_id = members[0]["id"]
    resident = owner.client.post(
        f"/api/v1/households/{household_id}/members",
        json={
            "display_name": "Istniejący profil",
            "role": "viewer",
            "is_guest": guest,
        },
        headers=headers(owner.client),
    )
    assert resident.status_code == 201
    return Home(owner, household_id, owner_member_id, resident.json()["id"])


def invite(
    household: Home, *, role: str = "viewer", key: str | None = None, new_resident: bool = False
) -> dict:
    created = household.owner.client.post(
        f"/api/v1/households/{household.id}/invite",
        json={
            "role": role,
            "member_id": None if new_resident else household.resident_id,
        },
        headers=headers(household.owner.client, key),
    )
    assert created.status_code == 201
    assert created.headers["cache-control"] == "no-store"
    return created.json()


def accept(recipient: Person, token: str, key: str | None = None):
    return recipient.client.post(
        "/api/v1/household-invitations/accept",
        json={"token": token},
        headers=headers(recipient.client, key),
    )


def audit_count(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(AuditEvent)) or 0


def action_count(engine: Engine, action: str) -> int:
    with Session(engine) as session:
        return (
            session.scalar(
                select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action)
            )
            or 0
        )


def profile_snapshot(engine: Engine, member_id: str) -> list:
    with Session(engine) as session:
        rows = session.scalars(
            select(NutritionProfile)
            .where(NutritionProfile.member_id == UUID(member_id))
            .order_by(NutritionProfile.version)
        ).all()
        return [
            (
                row.id,
                row.version,
                row.kcal_target,
                row.protein_target_g,
                row.carbs_target_g,
                row.fat_target_g,
                row.valid_from,
                row.source,
                row.created_at,
            )
            for row in rows
        ]


def target_history(household: Home) -> list:
    return household.owner.client.get(
        f"/api/v1/households/{household.id}/members/"
        f"{household.resident_id}/nutrition-target/history"
    ).json()["history"]


def seed_target_history(household: Home) -> list:
    for version, energy in enumerate(["2700.001", "1600"]):
        saved = household.owner.client.put(
            f"/api/v1/households/{household.id}/members/{household.resident_id}/nutrition-target",
            json={
                "expected_version": version,
                "kcal_target": energy,
                "protein_target_g": "0",
                "carbs_target_g": None,
                "fat_target_g": "1.234",
                "goal_type": "custom",
                "valid_from": datetime.now(ZoneInfo("Europe/Warsaw")).date().isoformat(),
            },
            headers=headers(household.owner.client),
        )
        assert saved.status_code == 200
    return target_history(household)


def member(household: Home) -> dict:
    people = household.owner.client.get(f"/api/v1/households/{household.id}/members").json()[
        "members"
    ]
    return next(item for item in people if item["id"] == household.resident_id)


def access(
    household: Home,
    *,
    enabled: bool,
    role: str = "viewer",
    version: int | None = None,
    key: str | None = None,
):
    revision = member(household)["access_version"] if version is None else version
    return household.owner.client.put(
        f"/api/v1/households/{household.id}/members/{household.resident_id}/access",
        json={"expected_version": revision, "role": role, "access_enabled": enabled},
        headers=headers(household.owner.client, key),
    )


def test_creation_ttl_list_and_idempotency_never_persist_raw_code(
    clients: ClientFactory,
    migrated_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    household = home(clients)
    key = str(uuid4())
    created = invite(household, key=key)
    token = created["token"]
    assert len(token) == 64
    replay = invite(household, key=key)
    same_token = replay["token"] == token
    assert same_token
    assert {name: value for name, value in created.items() if name != "token"} == {
        name: value for name, value in replay.items() if name != "token"
    }
    listed = household.owner.client.get(f"/api/v1/households/{household.id}/invitations")
    assert listed.status_code == 200
    assert listed.headers["cache-control"] == "no-store"
    assert len(listed.json()["invitations"]) == 1
    forbidden = {"token", "token_hash", "private_nonce"}
    assert not forbidden.intersection(listed.json()["invitations"][0])
    with Session(migrated_engine) as session:
        invitation = session.get(HouseholdInvitation, UUID(created["id"]))
        assert invitation is not None
        assert invitation.expires_at - invitation.created_at == timedelta(hours=24)
        matches_hash = invitation.token_hash == sha256(token.encode()).hexdigest()
        assert matches_hash
        stored = session.scalars(select(IdempotencyRecord)).all()
        raw_in_results = any(token in json.dumps(record.result) for record in stored)
        assert not raw_in_results
        assert session.scalar(select(func.count()).select_from(HouseholdInvitation)) == 1
    raw_in_logs = token in caplog.text
    assert not raw_in_logs


def test_link_revoke_and_restore_preserve_resident_and_exact_profile_history(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    history = seed_target_history(household)
    stored_profiles = profile_snapshot(migrated_engine, household.resident_id)
    created = invite(household)
    key = str(uuid4())
    before = audit_count(migrated_engine)
    accepted = accept(recipient, created["token"], key)
    assert accepted.status_code == 200
    assert accepted.json()["member"]["id"] == household.resident_id
    assert accepted.json()["household"]["role"] == "viewer"
    assert target_history(household) == history
    original = member(household)
    assert original["version"] == 2
    assert original["user_id"] == recipient.user_id
    assert original["access_enabled"] is True
    assert audit_count(migrated_engine) == before + 2
    assert action_count(migrated_engine, "invitation.accepted") == 1
    assert action_count(migrated_engine, "member.access_linked") == 1
    assert accept(recipient, created["token"], key).status_code == 200
    assert audit_count(migrated_engine) == before + 2
    assert accept(recipient, created["token"]).status_code == 409
    base = f"/api/v1/households/{household.id}"
    assert recipient.client.get(base + "/members").status_code == 200
    denied = recipient.client.put(
        base + f"/members/{household.resident_id}/nutrition-target",
        json={
            "expected_version": 2,
            "kcal_target": "1800",
            "protein_target_g": None,
            "carbs_target_g": None,
            "fat_target_g": None,
            "goal_type": "custom",
            "valid_from": datetime.now(ZoneInfo("Europe/Warsaw")).date().isoformat(),
        },
        headers=headers(recipient.client),
    )
    assert denied.status_code == 403
    revoked = access(household, enabled=False)
    assert revoked.status_code == 200
    assert revoked.json()["access_version"] == original["access_version"] + 1
    assert recipient.client.get("/api/v1/households").json()["households"] == []
    for suffix in [
        "",
        "/members",
        "/meal-slot-presets",
        f"/members/{household.resident_id}/nutrition-target/history",
    ]:
        assert recipient.client.get(base + suffix).status_code == 404
    assert accept(recipient, created["token"], key).status_code == 404
    assert target_history(household) == history
    assert profile_snapshot(migrated_engine, household.resident_id) == stored_profiles
    with Session(migrated_engine) as session:
        resident = session.get(HouseholdMember, UUID(household.resident_id))
        assert resident is not None
        assert resident.active is True and resident.access_enabled is False
        assert resident.target_revision == 2 and str(resident.user_id) == recipient.user_id
        assert session.scalar(select(func.count()).select_from(NutritionProfile)) == 2
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 2
    stale = access(household, enabled=True, role="editor", version=original["access_version"])
    assert stale.status_code == 409
    restored = access(household, enabled=True, role="editor")
    assert restored.status_code == 200
    assert recipient.client.get(base).json()["role"] == "editor"
    assert target_history(household) == history
    assert profile_snapshot(migrated_engine, household.resident_id) == stored_profiles


@pytest.mark.parametrize("mode", ["expired", "revoked"])
def test_expired_and_revoked_codes_cannot_link_a_recipient(
    clients: ClientFactory,
    migrated_engine: Engine,
    mode: str,
) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household)
    if mode == "expired":
        with Session(migrated_engine) as session, session.begin():
            invitation = session.get(HouseholdInvitation, UUID(created["id"]))
            assert invitation is not None
            invitation.expires_at = datetime.now(UTC) - timedelta(seconds=30)
    else:
        revoked = household.owner.client.post(
            f"/api/v1/households/{household.id}/invitations/{created['id']}/revoke",
            json={"expected_version": created["version"]},
            headers=headers(household.owner.client),
        )
        assert revoked.status_code == 200
    before = audit_count(migrated_engine)
    denied = accept(recipient, created["token"])
    assert denied.status_code == 410
    assert member(household)["user_id"] is None
    assert audit_count(migrated_engine) == before


def test_old_code_and_owner_creation_replay_fail_closed_after_secret_rotation(
    clients: ClientFactory,
    invitation_settings: Settings,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    key = str(uuid4())
    created = invite(household, key=key)
    rotated = invitation_settings.model_copy(update={"session_secret": SecretStr("new-" + SECRET)})
    before = audit_count(migrated_engine)
    for identity in [recipient, household.owner]:
        with TestClient(create_app(rotated)) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": identity.email, "password": PASSWORD},
                headers={"Origin": ORIGIN},
            )
            assert login.status_code == 200
            if identity is recipient:
                denied = client.post(
                    "/api/v1/household-invitations/accept",
                    json={"token": created["token"]},
                    headers=headers(client),
                )
            else:
                denied = client.post(
                    f"/api/v1/households/{household.id}/invite",
                    json={"role": "viewer", "member_id": household.resident_id},
                    headers=headers(client, key),
                )
            assert denied.status_code == 409
            assert denied.json()["error_code"] == "INVITATION_SECRET_CHANGED"
    assert member(household)["user_id"] is None
    assert audit_count(migrated_engine) == before


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_only_household_owner_can_manage_invitations_or_account_access(
    clients: ClientFactory,
    role: str,
) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household, role=role)
    assert accept(recipient, created["token"]).status_code == 200
    base = f"/api/v1/households/{household.id}"
    assert recipient.client.get(base + "/invitations").status_code == 403
    attempted = recipient.client.post(
        base + "/invite",
        json={"role": "editor", "member_id": None},
        headers=headers(recipient.client),
    )
    assert attempted.status_code == 403
    changed = recipient.client.put(
        base + f"/members/{household.resident_id}/access",
        json={
            "expected_version": member(household)["access_version"],
            "role": "editor",
            "access_enabled": True,
        },
        headers=headers(recipient.client),
    )
    assert changed.status_code == 403


def test_guest_foreign_member_and_owner_role_escalation_are_denied(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, foreign = home(clients, guest=True), home(clients)
    base = f"/api/v1/households/{household.id}"
    before = audit_count(migrated_engine)
    for member_id, role, status in [
        (household.resident_id, "viewer", 422),
        (foreign.resident_id, "viewer", 404),
        (None, "owner", 422),
    ]:
        denied = household.owner.client.post(
            base + "/invite",
            json={"member_id": member_id, "role": role},
            headers=headers(household.owner.client),
        )
        assert denied.status_code == status
    assert audit_count(migrated_engine) == before
    created = invite(foreign)
    assert (
        household.owner.client.get(f"/api/v1/households/{foreign.id}/invitations").status_code
        == 404
    )
    confused = household.owner.client.post(
        base + f"/invitations/{created['id']}/revoke",
        json={"expected_version": created["version"]},
        headers=headers(household.owner.client),
    )
    assert confused.status_code == 404


def test_owner_cannot_revoke_or_demote_own_account_access(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household = home(clients)
    base = f"/api/v1/households/{household.id}/members/{household.owner_member_id}/access"
    before = audit_count(migrated_engine)
    denied = household.owner.client.put(
        base,
        json={"expected_version": 0, "role": "viewer", "access_enabled": False},
        headers=headers(household.owner.client),
    )
    assert denied.status_code == 409
    assert denied.json()["error_code"] == "OWNER_ACCESS_PROTECTED"
    assert audit_count(migrated_engine) == before
    with Session(migrated_engine) as session:
        owner = session.get(HouseholdMember, UUID(household.owner_member_id))
        assert owner is not None and owner.role == "owner" and owner.access_enabled is True


@pytest.mark.parametrize("invalid", ["origin", "csrf"])
def test_invite_acceptance_rejects_untrusted_origin_or_csrf_without_consuming_code(
    clients: ClientFactory,
    migrated_engine: Engine,
    invalid: str,
) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household)
    bad = headers(recipient.client)
    bad["Origin" if invalid == "origin" else "X-CSRF-Token"] = (
        "https://evil.example" if invalid == "origin" else "x" * 64
    )
    before = audit_count(migrated_engine)
    denied = recipient.client.post(
        "/api/v1/household-invitations/accept", json={"token": created["token"]}, headers=bad
    )
    assert denied.status_code == 403
    assert audit_count(migrated_engine) == before
    assert accept(recipient, created["token"]).status_code == 200


def test_distinct_recipients_racing_one_invitation_link_only_one_existing_profile(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household = home(clients)
    history = seed_target_history(household)
    recipients = [person(clients), person(clients)]
    created = invite(household)
    incoming = [headers(recipient.client) for recipient in recipients]
    gate = Barrier(2)
    before = audit_count(migrated_engine)

    def join(index: int) -> int:
        gate.wait(timeout=10)
        return (
            recipients[index]
            .client.post(
                "/api/v1/household-invitations/accept",
                json={"token": created["token"]},
                headers=incoming[index],
            )
            .status_code
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(join, [0, 1]))
    assert sorted(statuses) == [200, 409]
    assert member(household)["user_id"] == recipients[statuses.index(200)].user_id
    assert target_history(household) == history
    assert audit_count(migrated_engine) == before + 2
    assert action_count(migrated_engine, "invitation.accepted") == 1
    assert action_count(migrated_engine, "member.access_linked") == 1
    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 2
        invitation = session.get(HouseholdInvitation, UUID(created["id"]))
        assert invitation is not None and invitation.accepted_at is not None
        assert str(invitation.accepted_by_user_id) == recipients[statuses.index(200)].user_id


def test_accept_revoke_race_has_one_commit_and_no_partial_account_link(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household)
    recipient_headers, owner_headers = headers(recipient.client), headers(household.owner.client)
    gate = Barrier(2)
    before = audit_count(migrated_engine)

    def execute(operation: str) -> int:
        gate.wait(timeout=10)
        if operation == "accept":
            return recipient.client.post(
                "/api/v1/household-invitations/accept",
                json={"token": created["token"]},
                headers=recipient_headers,
            ).status_code
        return household.owner.client.post(
            f"/api/v1/households/{household.id}/invitations/{created['id']}/revoke",
            json={"expected_version": created["version"]},
            headers=owner_headers,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted, revoked = list(executor.map(execute, ["accept", "revoke"]))
    assert (accepted, revoked) in {(200, 409), (410, 200)}
    assert audit_count(migrated_engine) == before + (2 if accepted == 200 else 1)
    assert action_count(migrated_engine, "invitation.accepted") == (1 if accepted == 200 else 0)
    assert action_count(migrated_engine, "member.access_linked") == (1 if accepted == 200 else 0)
    assert action_count(migrated_engine, "invitation.revoked") == (1 if revoked == 200 else 0)
    resident = member(household)
    assert resident["user_id"] == (recipient.user_id if accepted == 200 else None)
    with Session(migrated_engine) as session:
        invitation = session.get(HouseholdInvitation, UUID(created["id"]))
        assert invitation is not None
        assert (invitation.accepted_at is not None) != (invitation.revoked_at is not None)
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 2


def test_new_resident_acceptance_and_replay_create_only_one_member(clients: ClientFactory) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household, new_resident=True)
    key = str(uuid4())
    accepted = accept(recipient, created["token"], key)
    assert accepted.status_code == 200
    linked_id = accepted.json()["member"]["id"]
    assert linked_id not in {household.owner_member_id, household.resident_id}
    assert accepted.json()["member"]["nutrition_target"] is None
    replay = accept(recipient, created["token"], key)
    assert replay.status_code == 200 and replay.json()["member"]["id"] == linked_id
    people = household.owner.client.get(f"/api/v1/households/{household.id}/members").json()[
        "members"
    ]
    assert len(people) == 3


def test_both_recipients_peek_before_household_unlock_cannot_consume_new_resident_invite_twice(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household = home(clients)
    recipients = [person(clients), person(clients)]
    created = invite(household, new_resident=True)
    incoming = [headers(recipient.client) for recipient in recipients]
    before = audit_count(migrated_engine)

    def join(index: int) -> int:
        return (
            recipients[index]
            .client.post(
                "/api/v1/household-invitations/accept",
                json={"token": created["token"]},
                headers=incoming[index],
            )
            .status_code
        )

    # Both requests must complete the token peek and block on the same real DB row.
    # Releasing this lock reproduces a stale identity-map read deterministically.
    with migrated_engine.connect() as blocker:
        transaction = blocker.begin()
        blocker.execute(
            select(Household.id).where(Household.id == UUID(household.id)).with_for_update()
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(join, index) for index in range(2)]
            try:
                deadline = monotonic() + 4
                waiting = 0
                while monotonic() < deadline:
                    with migrated_engine.connect() as observer:
                        waiting = observer.scalar(
                            text(
                                "SELECT count(*) FROM pg_stat_activity "
                                "WHERE datname=current_database() AND wait_event_type='Lock' "
                                "AND query LIKE '%FROM households%'"
                            )
                        )
                    if waiting == 2:
                        break
                    sleep(0.01)
                assert waiting == 2
            finally:
                transaction.commit()
            statuses = [future.result(timeout=10) for future in futures]
    assert sorted(statuses) == [200, 409]
    assert audit_count(migrated_engine) == before + 2
    assert action_count(migrated_engine, "invitation.accepted") == 1
    assert action_count(migrated_engine, "member.access_linked") == 1
    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 3
        invitation = session.get(HouseholdInvitation, UUID(created["id"]))
        assert invitation is not None and invitation.version == 2
        assert str(invitation.accepted_by_user_id) == recipients[statuses.index(200)].user_id


def wait_for_household_lock(engine: Engine) -> None:
    """Observe a real waiter after its earlier unprotected ORM read has completed."""
    deadline = monotonic() + 4
    waiting = 0
    while monotonic() < deadline:
        with engine.connect() as observer:
            waiting = observer.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname=current_database() AND wait_event_type='Lock' "
                    "AND query LIKE '%FROM households%'"
                )
            )
        if waiting == 1:
            return
        sleep(0.01)
    assert waiting == 1, "Request did not reach the held PostgreSQL household lock"


def test_revoke_after_token_peek_is_observed_before_acceptance_commits(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    history = seed_target_history(household)
    snapshot = profile_snapshot(migrated_engine, household.resident_id)
    created = invite(household)
    incoming = headers(recipient.client)
    before = audit_count(migrated_engine)
    with migrated_engine.connect() as blocker:
        transaction = blocker.begin()
        blocker.execute(
            select(Household.id).where(Household.id == UUID(household.id)).with_for_update()
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                recipient.client.post,
                "/api/v1/household-invitations/accept",
                json={"token": created["token"]},
                headers=incoming,
            )
            try:
                wait_for_household_lock(migrated_engine)
                # Fixture mutation stands for the revoke transaction that wins this lock.
                blocker.execute(
                    update(HouseholdInvitation)
                    .where(HouseholdInvitation.id == UUID(created["id"]))
                    .values(revoked_at=datetime.now(UTC), version=2)
                )
            finally:
                transaction.commit()
            denied = pending.result(timeout=10)
    assert denied.status_code == 410
    assert denied.json()["error_code"] == "INVITATION_UNAVAILABLE"
    assert audit_count(migrated_engine) == before
    assert action_count(migrated_engine, "invitation.accepted") == 0
    assert action_count(migrated_engine, "member.access_linked") == 0
    assert member(household)["user_id"] is None
    assert target_history(household) == history
    assert profile_snapshot(migrated_engine, household.resident_id) == snapshot
    with Session(migrated_engine) as session:
        invitation = session.get(HouseholdInvitation, UUID(created["id"]))
        assert invitation is not None and invitation.accepted_at is None
        assert invitation.accepted_by_user_id is None and invitation.version == 2
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 2
        assert session.scalar(
            select(func.count()).select_from(IdempotencyRecord).where(
                IdempotencyRecord.actor_user_id == UUID(recipient.user_id)
            )
        ) == 0


def test_household_listing_refreshes_role_after_waiting_for_downgrade(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    created = invite(household, role="editor")
    assert accept(recipient, created["token"]).status_code == 200
    before = audit_count(migrated_engine)
    with migrated_engine.connect() as blocker:
        transaction = blocker.begin()
        blocker.execute(
            select(Household.id).where(Household.id == UUID(household.id)).with_for_update()
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(recipient.client.get, "/api/v1/households")
            try:
                wait_for_household_lock(migrated_engine)
                blocker.execute(
                    update(HouseholdMember)
                    .where(HouseholdMember.id == UUID(household.resident_id))
                    .values(role="viewer", access_version=2)
                )
            finally:
                transaction.commit()
            listed = pending.result(timeout=10)
    assert listed.status_code == 200
    assert listed.json()["households"] == [{
        "id": household.id,
        "name": "Dom QA",
        "timezone": "Europe/Warsaw",
        "currency": "PLN",
        "role": "viewer",
        "source": "user_created",
        "capabilities": {"can_edit": False, "can_manage_access": False},
    }]
    assert audit_count(migrated_engine) == before


def test_target_write_waiting_for_access_revocation_cannot_commit_old_permissions(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    household, recipient = home(clients), person(clients)
    history = seed_target_history(household)
    snapshot = profile_snapshot(migrated_engine, household.resident_id)
    created = invite(household, role="editor")
    assert accept(recipient, created["token"]).status_code == 200
    incoming = headers(recipient.client)
    before = audit_count(migrated_engine)
    with migrated_engine.connect() as blocker:
        transaction = blocker.begin()
        blocker.execute(
            select(Household.id).where(Household.id == UUID(household.id)).with_for_update()
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                recipient.client.put,
                f"/api/v1/households/{household.id}/members/"
                f"{household.resident_id}/nutrition-target",
                json={
                    "expected_version": 2,
                    "kcal_target": "1900",
                    "protein_target_g": "0",
                    "carbs_target_g": None,
                    "fat_target_g": "1.234",
                    "goal_type": "custom",
                    "valid_from": datetime.now(ZoneInfo("Europe/Warsaw")).date().isoformat(),
                },
                headers=incoming,
            )
            try:
                wait_for_household_lock(migrated_engine)
                blocker.execute(
                    update(HouseholdMember)
                    .where(HouseholdMember.id == UUID(household.resident_id))
                    .values(access_enabled=False, access_version=2)
                )
            finally:
                transaction.commit()
            denied = pending.result(timeout=10)
    assert denied.status_code == 404
    assert audit_count(migrated_engine) == before
    assert target_history(household) == history
    assert profile_snapshot(migrated_engine, household.resident_id) == snapshot
    assert member(household)["version"] == 2
    assert member(household)["access_enabled"] is False
    assert member(household)["user_id"] == recipient.user_id
