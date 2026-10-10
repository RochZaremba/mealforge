from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError

from mealforge.application import create_app
from mealforge.core.api import now
from mealforge.core.config import Settings
from mealforge.core.database import session_factory
from mealforge.households.models import AuditEvent, Household, IdempotencyRecord, NutritionProfile
from mealforge.households.schemas import TargetInput
from mealforge.identity.models import AuthRateBucket, ServerSession, User

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:3000"
PASSWORD = "correct-horse-fuel-battery"


@pytest.fixture
def private_settings(postgres_settings: Settings) -> Settings:
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr("test-secret-for-mealforge-over-thirty-two-characters"),
        app_env="test",
    )


def login(client: TestClient, email: str = "owner@example.test", *, register: bool = True) -> str:
    if register:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": PASSWORD, "display_name": "Domownik"},
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 201, response.text
        assert client.get("/api/v1/auth/session").status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def headers(csrf: str, key: str | None = None) -> dict[str, str]:
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf, "Idempotency-Key": key or str(uuid4())}


def household(client: TestClient, csrf: str) -> str:
    response = client.post(
        "/api/v1/households", json={"name": "Wspólna kuchnia"}, headers=headers(csrf)
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def target(version: int = 0, **updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "expected_version": version,
        "kcal_target": "2700",
        "protein_target_g": None,
        "carbs_target_g": None,
        "fat_target_g": None,
        "goal_type": "maintenance",
        "valid_from": now().date().isoformat(),
    }
    return result | updates


def test_sessions_are_hashed_revocable_and_no_store(
    private_settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(private_settings)) as client:
        csrf = login(client)
        session = client.get("/api/v1/auth/session")
        assert session.json()["csrf_token"] == csrf
        assert session.headers["cache-control"] == "no-store"
        token = client.cookies["mealforge_session"]
        with session_factory(migrated_engine)() as db:
            record = db.scalar(select(ServerSession))
            assert record is not None and record.token_hash == sha256(token.encode()).hexdigest()
            user = db.scalar(select(User))
            assert user is not None and user.password_hash.startswith("$argon2id$")
            assert PASSWORD not in user.password_hash
        response = client.post("/api/v1/auth/logout", json={}, headers=headers(csrf))
        assert response.status_code == 204
        client.cookies.set("mealforge_session", token)
        assert client.get("/api/v1/auth/session").status_code == 401


def test_expired_session_cannot_mutate(private_settings: Settings, migrated_engine: Engine) -> None:
    with TestClient(create_app(private_settings)) as client:
        csrf = login(client)
        with session_factory(migrated_engine).begin() as db:
            record = db.scalar(select(ServerSession))
            assert record is not None
            record.expires_at = now() - timedelta(seconds=1)
        response = client.post("/api/v1/households", json={"name": "Dom"}, headers=headers(csrf))
        assert response.status_code == 401


def test_password_failures_throttle_and_keep_identifiers_private(
    private_settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(private_settings)) as client:
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": "unknown@example.test", "password": PASSWORD},
                headers={"Origin": ORIGIN},
            ).status_code
            for _ in range(9)
        ]
    assert statuses == [401] * 8 + [429]
    with session_factory(migrated_engine)() as db:
        rows = db.scalars(select(AuthRateBucket)).all()
        assert rows and all(
            len(row.bucket_key) == 64 and "unknown" not in row.bucket_key for row in rows
        )
        assert db.scalar(select(func.count()).select_from(ServerSession)) == 0


def test_onboarding_targets_history_warnings_and_repeated_slot_settings(
    private_settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(private_settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        owner = client.get(f"/api/v1/households/{hid}/members").json()["members"][0]
        assert owner["version"] == 0 and owner["nutrition_target"] is None
        second = client.post(
            f"/api/v1/households/{hid}/members",
            json={"display_name": "Druga osoba"},
            headers=headers(csrf),
        )
        assert second.status_code == 201 and second.json()["user_id"] is None
        path = f"/api/v1/households/{hid}/members/{owner['id']}/nutrition-target"
        first = client.put(path, json=target(), headers=headers(csrf))
        assert first.status_code == 200, first.text
        assert first.json()["protein_target_g"] is None and first.json()["warnings"] == []
        newer = client.put(
            path,
            json=target(
                1,
                kcal_target="2700.125",
                protein_target_g="0",
                carbs_target_g="0",
                fat_target_g="0",
            ),
            headers=headers(csrf),
        )
        assert newer.status_code == 200
        assert newer.json()["kcal_target"] == "2700.125"
        assert newer.json()["protein_target_g"] == "0" and newer.json()["warnings"]
        history = client.get(path + "/history").json()["history"]
        assert [row["version"] for row in history] == [2, 1]
        assert history[1] == first.json()
        slots_path = f"/api/v1/households/{hid}/meal-slot-presets"
        original = client.get(slots_path).json()
        assert len(original["slots"]) == 5
        assert [slot["repeat_weekly"] for slot in original["slots"]] == [
            True,
            False,
            False,
            False,
            True,
        ]
        slots = [
            {key: value for key, value in slot.items() if key != "ordering"}
            for slot in original["slots"]
        ]
        slots[0] |= {"name": "Własne śniadanie", "repeat_weekly": False, "default_share": "0.25"}
        slots.append(
            {
                "id": None,
                "name": "Szósty posiłek",
                "default_time": "21:15",
                "default_share": None,
                "repeat_weekly": False,
            }
        )
        saved = client.put(
            slots_path, json={"expected_version": 1, "slots": slots}, headers=headers(csrf)
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 2 and len(saved.json()["slots"]) == 6
        assert saved.json() == client.get(slots_path).json()
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(AuditEvent)) == 5


def test_target_future_dates_conflicts_and_transactional_replay(
    private_settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(private_settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        mid = client.get(f"/api/v1/households/{hid}/members").json()["members"][0]["id"]
        path = f"/api/v1/households/{hid}/members/{mid}/nutrition-target"
        future = target(valid_from=(now().date() + timedelta(days=2)).isoformat())
        assert client.put(path, json=future, headers=headers(csrf)).status_code == 422
        key = str(uuid4())
        first = client.put(path, json=target(), headers=headers(csrf, key))
        assert first.status_code == 200
        assert client.put(path, json=target(), headers=headers(csrf, key)).json() == first.json()
        assert (
            client.put(
                path, json=target(kcal_target="1600"), headers=headers(csrf, key)
            ).status_code
            == 409
        )
        assert client.put(path, json=target(), headers=headers(csrf)).status_code == 409
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(NutritionProfile)) == 1
            assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 2
            assert db.scalar(select(func.count()).select_from(AuditEvent)) == 2
        with pytest.raises(IntegrityError):
            with migrated_engine.begin() as connection:
                connection.execute(text("UPDATE nutrition_profiles SET kcal_target=1600"))
        for table in ("nutrition_profiles", "audit_events"):
            with pytest.raises(IntegrityError):
                with migrated_engine.begin() as connection:
                    connection.execute(text(f"DELETE FROM {table}"))


def test_concurrent_household_create_is_exactly_once(
    private_settings: Settings, migrated_engine: Engine
) -> None:
    app = create_app(private_settings)
    with TestClient(app) as client:
        csrf = login(client)
        token = client.cookies["mealforge_session"]
        key = str(uuid4())

        def create() -> dict[str, object]:
            with TestClient(app) as other:
                other.cookies.set("mealforge_session", token)
                response = other.post(
                    "/api/v1/households", json={"name": "Dom"}, headers=headers(csrf, key)
                )
                assert response.status_code == 201, response.text
                return response.json()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: create(), range(2)))
        assert results[0] == results[1]
    with session_factory(migrated_engine)() as db:
        assert db.scalar(select(func.count()).select_from(Household)) == 1
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 1


@pytest.mark.parametrize("bad", [0, -1, True, 1.0, "01", "1e3", "1.0001", "1000000", "-1", "NaN"])
def test_invalid_energy_targets_are_rejected_before_storage(bad: object) -> None:
    with pytest.raises(ValidationError):
        TargetInput.model_validate(target(kcal_target=bad))


def test_production_config_rejects_placeholder_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            session_secret=SecretStr("CHANGE_ME_GENERATE_WITH_CSPRNG_LONG"),
            trusted_origins=("https://mealforge.example",),
            database_url=SecretStr(
                "postgresql+psycopg://u:very-long-random-secret-for-db@db/mealforge"
            ),
        )


def test_auth_missing_configuration_and_actual_oversize_body() -> None:
    with TestClient(create_app(Settings())) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 503
        response = client.post(
            "/api/v1/auth/register",
            content=b" " * 17000,
            headers={"Content-Type": "application/json", "Origin": ORIGIN},
        )
        assert response.status_code == 413
        UUID(response.headers["x-request-id"])
