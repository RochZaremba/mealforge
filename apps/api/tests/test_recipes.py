import io
import json
from importlib.resources import files
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from test_onboarding import headers, household, login, target

from mealforge.application import create_app
from mealforge.core.api import ApiError
from mealforge.core.config import Settings
from mealforge.core.database import session_factory
from mealforge.households.models import (
    AuditEvent,
    Household,
    HouseholdMember,
    IdempotencyRecord,
    NutritionProfile,
)
from mealforge.recipes import demo, service
from mealforge.recipes.models import RecipeVersion


@pytest.fixture
def settings(postgres_settings: Settings) -> Settings:
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr("test-secret-for-mealforge-over-thirty-two-characters"),
        app_env="test",
    )


def recipe_input(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Moja potrawa",
        "instructions": ["Połącz zadeklarowane składniki."],
        "ingredients": [
            {"name": "Mój składnik", "amount": "12.001", "unit": "piece", "weight_state": "unknown"}
        ],
        "rights_attestation": "i_am_author",
    }
    return {**payload, **updates}


def test_packaged_originals_load_positive_and_honest() -> None:
    snapshots = service.original_snapshots()
    assert len(snapshots) == 3
    assert sum(len(row["ingredients"]) for row in snapshots) == 13
    assert all(
        row["planner_eligible"] is False and row["yield_mass_g"] is None for row in snapshots
    )
    assert all(all(value is None for value in row["nutrients"].values()) for row in snapshots)


@pytest.mark.parametrize("kind", ["missing", "oversize", "tamper", "invalid_json"])
def test_runtime_originals_fail_closed_on_absence_or_drift(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = files("mealforge.recipes").joinpath("originals.json").read_bytes()
    if kind == "oversize":
        original = b" " * 65537
    elif kind == "invalid_json":
        original = b"{}invalid"
    elif kind == "tamper":
        data = json.loads(original)
        data["recipes"][0]["ingredients"][0]["amount"] = "101"
        original = json.dumps(data).encode()

    def open_resource(mode: str) -> io.BytesIO:
        assert mode == "rb"
        if kind == "missing":
            raise FileNotFoundError
        return io.BytesIO(original)

    resource = SimpleNamespace(joinpath=lambda _: SimpleNamespace(open=open_resource))
    monkeypatch.setattr(service, "files", lambda _: resource)
    with pytest.raises(ApiError) as caught:
        service.original_snapshots()
    assert caught.value.status == 503
    assert caught.value.code == "DEMO_FIXTURE_UNAVAILABLE"


@pytest.mark.integration
def test_pre_c_persisted_idempotent_responses_have_legacy_sources(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        key = str(uuid4())
        created = client.post(
            "/api/v1/households", json={"name": "Prawdziwa kuchnia"}, headers=headers(csrf, key)
        )
        assert created.status_code == 201
        hid = created.json()["id"]
        mid = client.get(f"/api/v1/households/{hid}/members").json()["members"][0]["id"]
        target_key = str(uuid4())
        path = f"/api/v1/households/{hid}/members/{mid}/nutrition-target"
        assert client.put(path, json=target(), headers=headers(csrf, target_key)).status_code == 200
        with session_factory(migrated_engine).begin() as db:
            records = db.scalars(
                select(IdempotencyRecord).where(IdempotencyRecord.key.in_([key, target_key]))
            ).all()
            assert len(records) == 2
            for record in records:
                legacy = dict(record.result)
                legacy.pop("source")
                record.result = legacy
        replay = client.post(
            "/api/v1/households", json={"name": "Prawdziwa kuchnia"}, headers=headers(csrf, key)
        )
        assert replay.status_code == 201 and replay.json()["source"] == "user_created"
        replay_target = client.put(path, json=target(), headers=headers(csrf, target_key))
        assert replay_target.status_code == 200 and replay_target.json()["source"] == "user_set"
        with session_factory(migrated_engine).begin() as db:
            member = db.get(HouseholdMember, UUID(mid))
            assert member is not None
            member.access_enabled = False
        assert (
            client.post(
                "/api/v1/households", json={"name": "Prawdziwa kuchnia"}, headers=headers(csrf, key)
            ).status_code
            == 404
        )
        assert client.put(path, json=target(), headers=headers(csrf, target_key)).status_code == 404


@pytest.mark.integration
def test_global_demo_and_household_keys_cannot_cross_replay(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        key = str(uuid4())
        assert (
            client.post(
                "/api/v1/households", json={"name": "Kuchnia"}, headers=headers(csrf, key)
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/households/demo",
                json={"confirmation": "create_separate_demo"},
                headers=headers(csrf, key),
            ).status_code
            == 409
        )
        demo_key = str(uuid4())
        assert (
            client.post(
                "/api/v1/households/demo",
                json={"confirmation": "create_separate_demo"},
                headers=headers(csrf, demo_key),
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/households", json={"name": "Kuchnia"}, headers=headers(csrf, demo_key)
            ).status_code
            == 409
        )
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(Household)) == 2


@pytest.mark.integration
def test_recipe_retry_returns_original_version_and_records_references(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipes"
        key = str(uuid4())
        first = client.post(path, json=recipe_input(), headers=headers(csrf, key))
        assert first.status_code == 201
        rid = first.json()["id"]
        updated = client.put(
            path + "/" + rid,
            json=recipe_input(expected_version=1, title="Zmieniona potrawa"),
            headers=headers(csrf),
        )
        assert updated.status_code == 200 and updated.json()["version"] == 2
        assert (
            client.post(path, json=recipe_input(), headers=headers(csrf, key)).json()
            == first.json()
        )
        with session_factory(migrated_engine)() as db:
            record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == key))
            assert record is not None and set(record.result) == {"recipe_id", "version"}
            assert db.scalar(select(func.count()).select_from(RecipeVersion)) == 2


@pytest.mark.integration
def test_demo_failure_mid_transaction_rolls_back_every_private_row(
    settings: Settings, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = demo.new_recipe
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ApiError(503, "DEMO_FIXTURE_UNAVAILABLE", "Dane demonstracyjne nie są dostępne.")
        return original(*args, **kwargs)

    monkeypatch.setattr(demo, "new_recipe", fail_second)
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        response = client.post(
            "/api/v1/households/demo",
            json={"confirmation": "create_separate_demo"},
            headers=headers(csrf),
        )
        assert response.status_code == 503 and calls == 2
        with session_factory(migrated_engine)() as db:
            for table in (
                Household,
                HouseholdMember,
                NutritionProfile,
                RecipeVersion,
                AuditEvent,
                IdempotencyRecord,
            ):
                assert db.scalar(select(func.count()).select_from(table)) == 0


@pytest.mark.integration
def test_near_body_budget_five_utf8_snapshots_fit_response_budget(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipes"
        payload = recipe_input(
            ingredients=[
                {"name": "ę" * 60, "amount": "1.001", "unit": "unknown", "weight_state": "unknown"}
                for _ in range(40)
            ]
        )
        steps = ["ę" * 200]
        while (
            len(
                json.dumps(
                    {**payload, "instructions": steps + ["ę" * 200], "expected_version": 1},
                    ensure_ascii=False,
                ).encode()
            )
            < 16300
        ):
            steps.append("ę" * 200)
        payload["instructions"] = steps
        response = client.post(
            path,
            content=json.dumps(payload, ensure_ascii=False).encode(),
            headers={**headers(csrf), "Content-Type": "application/json"},
        )
        assert response.status_code == 201
        rid = response.json()["id"]
        for version in range(1, 6):
            response = client.put(
                path + "/" + rid,
                content=json.dumps(
                    {**payload, "expected_version": version}, ensure_ascii=False
                ).encode(),
                headers={**headers(csrf), "Content-Type": "application/json"},
            )
            assert response.status_code == 200
        history = client.get(path + "/" + rid + "/history?limit=5")
        assert history.status_code == 200 and len(history.content) < 262144
        assert len(history.json()["history"]) == 5 and history.json()["next_before_version"] == 2
        assert (
            client.get(path + "/" + rid + "/history?before_version=2").json()["history"][0][
                "version"
            ]
            == 1
        )
