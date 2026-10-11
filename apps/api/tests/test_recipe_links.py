import io
import json
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from test_onboarding import headers, household, login

from mealforge.application import create_app
from mealforge.core.api import ApiError
from mealforge.core.config import Settings
from mealforge.core.database import session_factory
from mealforge.households.models import AuditEvent, IdempotencyRecord
from mealforge.recipes.links import registry, routes
from mealforge.recipes.links.models import RecipeLink


@pytest.fixture
def settings(postgres_settings: Settings) -> Settings:
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr("test-secret-for-mealforge-over-thirty-two-characters"),
        app_env="test",
    )


def link_input(url: str = "https://example.org/dish#own-location") -> dict[str, object]:
    return {
        "user_title": "Moja nazwa źródła",
        "source_url": url,
        "own_note": "Moja własna notatka: 0 kcal / bez glutenu / pasteryzowane.",
        "own_contribution_attestation": "i_am_author_of_label_and_note",
    }


def test_packaged_registry_loads_the_whole_audited_metadata() -> None:
    data = registry.load_source_registry()
    packaged = json.loads(
        files("mealforge.recipes.links").joinpath("recipe_sources.json").read_bytes()
    )
    assert data == packaged
    assert data["default_mode"] == "link_only"
    assert len(data["sources"]) == 13
    assert all(source["automatic_fetch_enabled"] is False for source in data["sources"])


@pytest.mark.parametrize("kind", ["missing", "oversize", "tamper", "invalid_json"])
def test_source_registry_runtime_failure_has_no_success(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = files("mealforge.recipes.links").joinpath("recipe_sources.json").read_bytes()
    if kind == "oversize":
        content = b" " * 65537
    elif kind == "invalid_json":
        content = b"{}bad"
    elif kind == "tamper":
        data = json.loads(content)
        data["sources"][0]["domains"] = ["example.org"]
        content = json.dumps(data).encode()

    reads = []

    class BoundedStream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            reads.append(size)
            return super().read(size)

    def open_resource(mode: str) -> BoundedStream:
        assert mode == "rb"
        if kind == "missing":
            raise FileNotFoundError
        return BoundedStream(content)

    monkeypatch.setattr(
        registry,
        "files",
        lambda _: SimpleNamespace(joinpath=lambda _: SimpleNamespace(open=open_resource)),
    )
    with pytest.raises(ApiError) as caught:
        registry.load_source_registry()
    assert caught.value.status == 503 and caught.value.code == "SOURCE_REGISTRY_UNAVAILABLE"
    assert reads == ([] if kind == "missing" else [65537])


@pytest.mark.integration
def test_known_provider_rights_never_promote_link_and_classification_stays_frozen(
    settings: Settings, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipe-links"
        key = str(uuid4())
        payload = link_input("https://api.nal.usda.gov/own-bookmark#own-location")
        created = client.post(path, json=payload, headers=headers(csrf, key))
        assert created.status_code == 201
        data = created.json()
        assert data["source_id"] == "usda_fdc"
        assert data["license"] is None and data["status"] == "link_only"
        assert data["planner_eligible"] is False and data["automatic_fetch_enabled"] is False
        assert data["nutrition_status"] == "unknown" and data["allergen_status"] == "unknown"
        assert data["source_url"].endswith("#own-location") and not data["canonical_url"].endswith(
            "#own-location"
        )
        monkeypatch.setattr(
            routes, "load_source_registry", lambda: {"sources": [], "checked_at": "2000-01-01"}
        )
        assert client.post(path, json=payload, headers=headers(csrf, key)).json() == data
        assert client.get(path + "/" + data["id"]).json() == data
        with session_factory(migrated_engine)() as db:
            record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == key))
            assert record is not None and record.result == {"link_id": data["id"]}


@pytest.mark.integration
def test_distinct_sessions_duplicate_commit_exactly_once(
    settings: Settings, migrated_engine: Engine
) -> None:
    app = create_app(settings)
    with TestClient(app) as first, TestClient(app) as second:
        first_csrf = login(first)
        second_csrf = login(second, register=False)
        hid = household(first, first_csrf)
        path = f"/api/v1/households/{hid}/recipe-links"
        with ThreadPoolExecutor(max_workers=2) as executor:
            attempts = [
                executor.submit(client.post, path, json=link_input(), headers=headers(csrf))
                for client, csrf in ((first, first_csrf), (second, second_csrf))
            ]
            replies = [attempt.result(timeout=10) for attempt in attempts]
        assert sorted(reply.status_code for reply in replies) == [201, 409]
        duplicate = next(reply for reply in replies if reply.status_code == 409)
        assert duplicate.json()["error_code"] == "RECIPE_LINK_EXISTS"
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(RecipeLink)) == 1
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.action == "recipe_link.created")
                )
                == 1
            )


@pytest.mark.integration
def test_registry_absence_and_failure_after_insert_are_atomic(
    settings: Settings, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipe-links"

        def fail(*args: object, **kwargs: object) -> None:
            raise ApiError(503, "SOURCE_REGISTRY_UNAVAILABLE", "Rejestr źródeł nie jest dostępny.")

        with monkeypatch.context() as patch:
            patch.setattr(routes, "load_source_registry", fail)
            assert client.post(path, json=link_input(), headers=headers(csrf)).status_code == 503
        with monkeypatch.context() as patch:
            patch.setattr(routes, "audit", fail)
            assert client.post(path, json=link_input(), headers=headers(csrf)).status_code == 503
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(RecipeLink)) == 0
            assert (
                db.scalar(select(func.count()).select_from(AuditEvent)) == 1
            )  # Existing household only.
            assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 1


@pytest.mark.integration
def test_maximum_url_bytes_fit_postgres_unique_index_and_household_scope(
    settings: Settings, migrated_engine: Engine
) -> None:
    url = "https://example.org/" + "a" * (2048 - len("https://example.org/"))
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        first = household(client, csrf)
        second = household(client, csrf)
        for hid in (first, second):
            path = f"/api/v1/households/{hid}/recipe-links"
            created = client.post(path, json=link_input(url), headers=headers(csrf))
            assert created.status_code == 201
            assert len(created.json()["canonical_url"].encode()) == 2048
            assert client.post(path, json=link_input(url), headers=headers(csrf)).status_code == 409
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(RecipeLink)) == 2
