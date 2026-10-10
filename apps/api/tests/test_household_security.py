"""Independent W01-A acceptance against a real, isolated PostgreSQL database."""

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from threading import Barrier
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.orm import Session

from mealforge.core.config import Settings
from mealforge.households.models import AuditEvent, HouseholdMember, NutritionProfile
from mealforge.identity.models import ServerSession, User
from mealforge.main import create_app

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:3000"
PASSWORD = "QA-private-password-2026!"
ClientFactory = Callable[[], TestClient]


@pytest.fixture
def private_app(postgres_settings: Settings, migrated_engine: Engine) -> FastAPI:
    assert migrated_engine is not None
    return create_app(
        Settings(
            database_url=postgres_settings.database_url,
            session_secret=SecretStr("independent-QA-session-secret-" + "x" * 40),
            trusted_origins=(ORIGIN,),
            app_env="test",
        )
    )


@pytest.fixture
def new_client(private_app: FastAPI) -> Iterator[ClientFactory]:
    with ExitStack() as stack:
        yield lambda: stack.enter_context(TestClient(private_app))


def mutation_headers(client: TestClient, key: str | None = None) -> dict[str, str]:
    recovered = client.get("/api/v1/auth/session")
    assert recovered.status_code == 200
    return {
        "Origin": ORIGIN,
        "X-CSRF-Token": recovered.json()["csrf_token"],
        "Idempotency-Key": key or str(uuid4()),
    }


@dataclass
class Account:
    client: TestClient
    user_id: str
    household_id: str
    member_id: str
    create_key: str
    create_body: dict[str, str]


def account(new_client: ClientFactory) -> Account:
    client = new_client()
    email = f"qa-{uuid4().hex}@example.invalid"
    body = {"email": email, "password": PASSWORD, "display_name": "Osoba QA"}
    registered = client.post("/api/v1/auth/register", json=body, headers={"Origin": ORIGIN})
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert login.status_code == 200, login.text
    create_key = str(uuid4())
    create_body = {"name": f"Prywatny dom {uuid4().hex}"}
    household = client.post(
        "/api/v1/households", json=create_body, headers=mutation_headers(client, create_key)
    )
    assert household.status_code == 201, household.text
    household_id = household.json()["id"]
    members = client.get(f"/api/v1/households/{household_id}/members")
    assert members.status_code == 200
    own = next(
        item for item in members.json()["members"] if item["user_id"] == login.json()["user"]["id"]
    )
    assert own["nutrition_target"] is None
    return Account(
        client, login.json()["user"]["id"], household_id, own["id"], create_key, create_body
    )


def target_body(version: int = 0) -> dict[str, object]:
    return {
        "expected_version": version,
        "kcal_target": "2700.125",
        "protein_target_g": "170.25",
        "carbs_target_g": None,
        "fat_target_g": "0",
        "goal_type": "custom",
        "valid_from": datetime.now(ZoneInfo("Europe/Warsaw")).date().isoformat(),
    }


def target_path(owner: Account, member_id: str | None = None) -> str:
    return (
        f"/api/v1/households/{owner.household_id}/members/"
        f"{member_id or owner.member_id}/nutrition-target"
    )


def audit_count(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(AuditEvent)) or 0


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/session",
        "/api/v1/households",
        f"/api/v1/households/{UUID(int=1)}",
        f"/api/v1/households/{UUID(int=1)}/members",
        f"/api/v1/households/{UUID(int=1)}/meal-slot-presets",
    ],
)
def test_private_reads_require_authentication(new_client: ClientFactory, path: str) -> None:
    response = new_client().get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_two_households_and_foreign_member_paths_are_isolated(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    first, second = account(new_client), account(new_client)
    own_list = first.client.get("/api/v1/households").json()["households"]
    assert [item["id"] for item in own_list] == [first.household_id]
    before = audit_count(migrated_engine)
    foreign_base = f"/api/v1/households/{second.household_id}"
    for suffix in [
        "",
        "/members",
        "/meal-slot-presets",
        f"/members/{second.member_id}/nutrition-target/history",
    ]:
        response = first.client.get(foreign_base + suffix)
        assert response.status_code in {403, 404}
        assert second.create_body["name"] not in response.text
    foreign_target = f"{foreign_base}/members/{second.member_id}/nutrition-target"
    for path in [foreign_target, target_path(first, second.member_id)]:
        response = first.client.put(
            path, json=target_body(), headers=mutation_headers(first.client)
        )
        assert response.status_code in {403, 404}
    confused_history = first.client.get(target_path(first, second.member_id) + "/history")
    assert confused_history.status_code in {403, 404}
    denied_member = first.client.post(
        foreign_base + "/members",
        json={"display_name": "Nieuprawniony"},
        headers=mutation_headers(first.client),
    )
    assert denied_member.status_code in {403, 404}
    assert audit_count(migrated_engine) == before
    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(NutritionProfile)) == 0


@pytest.mark.parametrize(
    "bad_headers",
    [
        {"Origin": "https://evil.example", "X-CSRF-Token": "correct"},
        {"X-CSRF-Token": "correct"},
        {"Origin": ORIGIN},
        {"Origin": ORIGIN, "X-CSRF-Token": "x" * 64},
    ],
)
def test_origin_and_csrf_rejection_cannot_mutate(
    new_client: ClientFactory,
    migrated_engine: Engine,
    bad_headers: dict[str, str],
) -> None:
    owner = account(new_client)
    valid = mutation_headers(owner.client)
    headers = {"Idempotency-Key": str(uuid4()), **bad_headers}
    if headers.get("X-CSRF-Token") == "correct":
        headers["X-CSRF-Token"] = valid["X-CSRF-Token"]
    before = audit_count(migrated_engine)
    response = owner.client.post(
        f"/api/v1/households/{owner.household_id}/members",
        json={"display_name": "Nie zapisuj"},
        headers=headers,
    )
    assert response.status_code == 403
    assert audit_count(migrated_engine) == before
    assert (
        len(owner.client.get(f"/api/v1/households/{owner.household_id}/members").json()["members"])
        == 1
    )


def test_csrf_from_another_session_is_rejected(new_client: ClientFactory) -> None:
    first, second = account(new_client), account(new_client)
    foreign_headers = mutation_headers(second.client)
    response = first.client.put(target_path(first), json=target_body(), headers=foreign_headers)
    assert response.status_code == 403


@pytest.mark.parametrize("inactive", [False, True])
def test_member_replay_rechecks_current_membership(
    new_client: ClientFactory,
    migrated_engine: Engine,
    inactive: bool,
) -> None:
    owner = account(new_client)
    headers = mutation_headers(owner.client)
    path = f"/api/v1/households/{owner.household_id}/members"
    body = {"display_name": "Druga osoba"}
    accepted = owner.client.post(path, json=body, headers=headers)
    assert accepted.status_code == 201
    with Session(migrated_engine) as session, session.begin():
        member = session.get(HouseholdMember, UUID(owner.member_id))
        assert member is not None
        member.role = "viewer"
        member.active = not inactive
    before = audit_count(migrated_engine)
    denied = owner.client.post(path, json=body, headers=headers)
    assert denied.status_code in {403, 404}
    assert accepted.json()["id"] not in denied.text
    assert audit_count(migrated_engine) == before


@pytest.mark.parametrize("inactive", [False, True])
def test_household_creation_replay_cannot_restore_revoked_owner_response(
    new_client: ClientFactory,
    migrated_engine: Engine,
    inactive: bool,
) -> None:
    owner = account(new_client)
    headers = mutation_headers(owner.client, owner.create_key)
    with Session(migrated_engine) as session, session.begin():
        member = session.get(HouseholdMember, UUID(owner.member_id))
        assert member is not None
        member.role = "viewer"
        member.active = not inactive
    response = owner.client.post("/api/v1/households", json=owner.create_body, headers=headers)
    assert response.status_code in {403, 404}
    assert owner.household_id not in response.text


def test_viewer_can_read_but_cannot_edit_any_household_state(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(new_client)
    with Session(migrated_engine) as session, session.begin():
        member = session.get(HouseholdMember, UUID(owner.member_id))
        assert member is not None
        member.role = "viewer"
    base = f"/api/v1/households/{owner.household_id}"
    slots = owner.client.get(base + "/meal-slot-presets")
    assert slots.status_code == 200
    assert owner.client.get(base + "/members").status_code == 200
    slot_body = {
        "expected_version": slots.json()["version"],
        "slots": [
            {key: value for key, value in slot.items() if key != "ordering"}
            for slot in slots.json()["slots"]
        ],
    }
    before = audit_count(migrated_engine)
    for method, path, body in [
        ("POST", base + "/members", {"display_name": "Zakazany"}),
        ("PUT", target_path(owner), target_body()),
        ("PUT", base + "/meal-slot-presets", slot_body),
    ]:
        response = owner.client.request(
            method, path, json=body, headers=mutation_headers(owner.client)
        )
        assert response.status_code == 403
    assert audit_count(migrated_engine) == before


def test_target_decimal_history_idempotency_and_conflict_are_atomic(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(new_client)
    path = target_path(owner)
    headers = mutation_headers(owner.client)
    before = audit_count(migrated_engine)
    accepted = owner.client.put(path, json=target_body(), headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.headers["cache-control"] == "no-store"
    target = accepted.json()
    assert target["version"] == 1
    assert Decimal(target["kcal_target"]) == Decimal("2700.125")
    assert Decimal(target["protein_target_g"]) == Decimal("170.25")
    assert target["carbs_target_g"] is None
    assert Decimal(target["fat_target_g"]) == 0
    assert audit_count(migrated_engine) == before + 1
    replay = owner.client.put(path, json=target_body(), headers=headers)
    assert replay.status_code == 200
    assert replay.json() == target
    assert audit_count(migrated_engine) == before + 1
    changed = {**target_body(), "protein_target_g": "171"}
    conflict = owner.client.put(path, json=changed, headers=headers)
    assert conflict.status_code == 409
    stale = owner.client.put(path, json=changed, headers=mutation_headers(owner.client))
    assert stale.status_code == 409
    assert audit_count(migrated_engine) == before + 1
    history = owner.client.get(path + "/history")
    assert history.status_code == 200
    assert history.json()["history"] == [target]
    second_body = {
        **target_body(1),
        "kcal_target": "1600",
        "carbs_target_g": "310.125",
        "fat_target_g": "85",
    }
    second = owner.client.put(path, json=second_body, headers=mutation_headers(owner.client))
    assert second.status_code == 200
    assert second.json()["kcal_target"] == "1600"
    assert any(item["code"] == "ENERGY_MACRO_MISMATCH" for item in second.json()["warnings"])
    history = owner.client.get(path + "/history").json()["history"]
    assert [row["version"] for row in history] == [2, 1]
    assert history[1] == target
    with Session(migrated_engine) as session:
        audits = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == "nutrition_target.created")
            .order_by(AuditEvent.created_at)
        ).all()
        assert [(row.version_before, row.version_after) for row in audits] == [(0, 1), (1, 2)]
        assert all(row.actor_user_id == UUID(owner.user_id) for row in audits)
        assert all(UUID(row.request_id) for row in audits)


def test_session_is_hashed_no_store_and_logout_revokes_stolen_cookie(
    new_client: ClientFactory,
    migrated_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner = account(new_client)
    cookie = owner.client.cookies.get("mealforge_session")
    assert cookie is not None
    token_hash = sha256(cookie.encode()).hexdigest()
    with Session(migrated_engine) as session:
        record = session.get(ServerSession, token_hash)
        user = session.get(User, UUID(owner.user_id))
        assert record is not None and user is not None
        assert record.token_hash != cookie
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
    for path in ["/api/v1/auth/session", "/api/v1/households", target_path(owner) + "/history"]:
        response = owner.client.get(path)
        assert response.headers["cache-control"] == "no-store"
        assert cookie not in response.text
        assert PASSWORD not in response.text
    logout = owner.client.post(
        "/api/v1/auth/logout", json={}, headers=mutation_headers(owner.client)
    )
    assert logout.status_code == 204
    replay = owner.client.get(
        "/api/v1/auth/session",
        headers={
            "Cookie": f"mealforge_session={cookie}",
        },
    )
    assert replay.status_code == 401
    with Session(migrated_engine) as session:
        record = session.get(ServerSession, token_hash)
        assert record is not None and record.revoked_at is not None
    columns = {column["name"] for column in inspect(migrated_engine).get_columns("audit_events")}
    assert not columns.intersection(
        {
            "payload",
            "password",
            "session_token",
            "kcal_target",
            "protein_target_g",
            "carbs_target_g",
            "fat_target_g",
        }
    )
    assert PASSWORD not in caplog.text and cookie not in caplog.text


def test_expired_session_cannot_access_private_data(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(new_client)
    cookie = owner.client.cookies.get("mealforge_session")
    assert cookie is not None
    with Session(migrated_engine) as session, session.begin():
        record = session.get(ServerSession, sha256(cookie.encode()).hexdigest())
        assert record is not None
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    response = owner.client.get(f"/api/v1/households/{owner.household_id}/members")
    assert response.status_code == 401


def test_forwarded_addresses_cannot_evade_peer_login_limit(new_client: ClientFactory) -> None:
    client = new_client()
    statuses = []
    for number in range(41):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"nonexistent-{number}-{uuid4().hex}@example.invalid",
                "password": PASSWORD,
            },
            headers={"Origin": ORIGIN, "X-Forwarded-For": f"198.51.100.{number + 1}"},
        )
        statuses.append(response.status_code)
    assert statuses[:40] == [401] * 40
    assert statuses[40] == 429


def test_slot_revision_foreign_ids_and_repeated_requests_are_atomic(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    first, second = account(new_client), account(new_client)
    path = f"/api/v1/households/{first.household_id}/meal-slot-presets"
    initial = first.client.get(path).json()
    assert len(initial["slots"]) == 5
    assert [slot["repeat_weekly"] for slot in initial["slots"]] == [True, False, False, False, True]
    slots = [
        {key: value for key, value in slot.items() if key != "ordering"}
        for slot in initial["slots"]
    ]
    slots[0].update(name="Własne śniadanie", repeat_weekly=False, default_share="0.2")
    body = {"expected_version": initial["version"], "slots": slots}
    headers = mutation_headers(first.client)
    before = audit_count(migrated_engine)
    saved = first.client.put(path, json=body, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == initial["version"] + 1
    assert saved.json()["slots"][0]["repeat_weekly"] is False
    assert first.client.put(path, json=body, headers=headers).json() == saved.json()
    assert audit_count(migrated_engine) == before + 1
    stale = first.client.put(path, json=body, headers=mutation_headers(first.client))
    assert stale.status_code == 409
    foreign = second.client.get(
        f"/api/v1/households/{second.household_id}/meal-slot-presets"
    ).json()
    bad = {
        "expected_version": saved.json()["version"],
        "slots": [{key: value for key, value in foreign["slots"][0].items() if key != "ordering"}],
    }
    denied = first.client.put(path, json=bad, headers=mutation_headers(first.client))
    assert denied.status_code in {403, 404}
    assert first.client.get(path).json() == saved.json()
    assert audit_count(migrated_engine) == before + 1


def test_member_payload_cannot_grant_access_to_another_account(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner, foreign = account(new_client), account(new_client)
    before = audit_count(migrated_engine)
    response = owner.client.post(
        f"/api/v1/households/{owner.household_id}/members",
        json={
            "display_name": "Bez zaproszenia",
            "user_id": foreign.user_id,
            "role": "editor",
        },
        headers=mutation_headers(owner.client),
    )
    assert response.status_code == 422
    assert audit_count(migrated_engine) == before
    assert [
        item["id"] for item in foreign.client.get("/api/v1/households").json()["households"]
    ] == [foreign.household_id]


def shared_editor(new_client: ClientFactory, engine: Engine) -> tuple[Account, Account]:
    owner, editor = account(new_client), account(new_client)
    # Invitations are a later slice. This legitimate membership is a DB fixture,
    # while every authorization/session/mutation below goes through the real API.
    with Session(engine) as session, session.begin():
        session.add(
            HouseholdMember(
                household_id=UUID(owner.household_id),
                user_id=UUID(editor.user_id),
                display_name="Edytor QA",
                role="editor",
                is_guest=False,
                active=True,
                target_revision=0,
            )
        )
    return owner, editor


@pytest.mark.parametrize("resource", ["target", "slots"])
def test_distinct_actors_racing_same_version_produce_one_commit(
    new_client: ClientFactory,
    migrated_engine: Engine,
    resource: str,
) -> None:
    owner, editor = shared_editor(new_client, migrated_engine)
    headers = [mutation_headers(owner.client), mutation_headers(editor.client)]
    if resource == "target":
        path = target_path(owner)
        bodies = [target_body(), {**target_body(), "kcal_target": "1600"}]
        expected_after = 1
    else:
        path = f"/api/v1/households/{owner.household_id}/meal-slot-presets"
        initial = owner.client.get(path).json()
        slots = [
            {key: value for key, value in slot.items() if key != "ordering"}
            for slot in initial["slots"]
        ]
        bodies = []
        for name in ["Śniadanie właściciela", "Śniadanie edytora"]:
            variant = [dict(slot) for slot in slots]
            variant[0]["name"] = name
            bodies.append({"expected_version": initial["version"], "slots": variant})
        expected_after = initial["version"] + 1
    gate = Barrier(2)
    before = audit_count(migrated_engine)

    def write(index: int) -> int:
        client = [owner.client, editor.client][index]
        gate.wait(timeout=10)
        return client.put(path, json=bodies[index], headers=headers[index]).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(write, [0, 1]))
    assert sorted(statuses) == [200, 409]
    assert audit_count(migrated_engine) == before + 1
    if resource == "target":
        history = owner.client.get(path + "/history").json()["history"]
        assert [item["version"] for item in history] == [expected_after]
        assert history[0]["kcal_target"] in {"2700.125", "1600"}
        with Session(migrated_engine) as session:
            assert session.scalar(select(func.count()).select_from(NutritionProfile)) == 1
    else:
        saved = owner.client.get(path).json()
        assert saved["version"] == expected_after
        assert len(saved["slots"]) == 5
        assert saved["slots"][0]["name"] in {"Śniadanie właściciela", "Śniadanie edytora"}


def test_independent_sessions_of_same_actor_share_exactly_once_create_key(
    new_client: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(new_client)
    email = owner.client.get("/api/v1/auth/session").json()["user"]["email"]
    other = new_client()
    login = other.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert login.status_code == 200
    assert other.cookies.get("mealforge_session") != owner.client.cookies.get("mealforge_session")
    key = str(uuid4())
    headers = [mutation_headers(owner.client, key), mutation_headers(other, key)]
    body = {"name": f"Jedna operacja {uuid4().hex}"}
    gate = Barrier(2)
    before = audit_count(migrated_engine)

    def create(index: int) -> tuple[int, dict]:
        client = [owner.client, other][index]
        gate.wait(timeout=10)
        response = client.post("/api/v1/households", json=body, headers=headers[index])
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(create, [0, 1]))
    assert [status for status, _ in responses] == [201, 201]
    assert responses[0][1] == responses[1][1]
    assert audit_count(migrated_engine) == before + 1
    households = owner.client.get("/api/v1/households").json()["households"]
    assert len(households) == 2
    assert len([item for item in households if item["name"] == body["name"]]) == 1
