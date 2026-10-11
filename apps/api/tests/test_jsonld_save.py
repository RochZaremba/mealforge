import json
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from test_jsonld import document
from test_onboarding import headers, household, login

from mealforge.application import create_app
from mealforge.core.api import ApiError, now
from mealforge.core.config import Settings
from mealforge.core.database import migration_config, session_factory
from mealforge.households.models import AuditEvent, IdempotencyRecord
from mealforge.importers import save
from mealforge.recipes.models import Recipe, RecipeVersion
from mealforge.recipes.schemas import RecipeSnapshot
from mealforge.recipes.service import new_recipe, original_snapshots

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(postgres_settings: Settings) -> Settings:
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr("test-secret-for-mealforge-over-thirty-two-characters"),
        app_env="test",
    )


def body(raw: str) -> dict[str, str]:
    return {"document": raw, "rights_attestation": "i_am_author"}


def edit_input(version: int = 1) -> dict[str, object]:
    return {
        "title": "Moja późniejsza wersja",
        "instructions": ["Zmienione własne instrukcje."],
        "ingredients": [
            {"name": "własny składnik", "amount": "1.001", "unit": "g", "weight_state": "raw"}
        ],
        "expected_version": version,
        "rights_attestation": "i_am_author",
    }


def nested_document(depth: int, name_size: int, steps: int) -> str:
    value: object = [{"@type": "HowToStep", "text": f"Połącz {i}."} for i in range(steps)]
    for level in range(depth):
        value = {
            "@type": "HowToSection",
            "name": str(level) + "s" * (name_size - 1),
            "itemListElement": value,
        }
    return document(recipeInstructions=value)


def test_atomic_import_edit_history_and_original_replay(
    settings: Settings, migrated_engine: Engine
) -> None:
    raw = document(
        recipeIngredient=[" 400 g cooked rice ", "woda wg potrzeby"],
        recipeInstructions=[
            {
                "@type": "HowToSection",
                "name": "Moja sekcja",
                "itemListElement": [{"@type": "HowToStep", "text": " Mieszaj. "}],
            }
        ],
        recipeYield=["3 kg 700 g", "4 porcje"],
        nutrition={"calories": "0 kcal"},
        author="Discarded-author-value",
        license="Discarded-license-value",
        storageMethod="Discarded-storage-value",
        url="https://discarded.example.org/source",
        image="https://discarded.example.org/picture",
    )
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipe-imports"
        key = str(uuid4())
        first = client.post(path, json=body(raw), headers=headers(csrf, key))
        assert first.status_code == 201
        original = first.json()
        rid = original["id"]
        origin = original["provenance"]["import_origin"]
        assert original["provenance"]["source_mode"] == "user_supplied_jsonld"
        assert origin["source_sha256"] == sha256(raw.encode()).hexdigest()
        assert origin["ingredients"] == [" 400 g cooked rice ", "woda wg potrzeby"]
        assert origin["instructions"] == [{"text": " Mieszaj. ", "section_path": ["Moja sekcja"]}]
        assert origin["recipe_yield_raw"] == ["3 kg 700 g", "4 porcje"]
        assert all(
            item["amount"] is None
            and item["unit"] == "unknown"
            and item["weight_state"] == "unknown"
            for item in original["ingredients"]
        )
        assert all(value is None for value in original["nutrients"].values())
        assert original["servings"] is None and original["yield_mass_g"] is None
        assert original["storage_method"] is None and original["planner_eligible"] is False
        recipe_path = f"/api/v1/households/{hid}/recipes/{rid}"
        updated = client.put(recipe_path, json=edit_input(), headers=headers(csrf))
        assert updated.status_code == 200 and updated.json()["version"] == 2
        assert updated.json()["provenance"]["source_mode"] == "user_authored"
        assert updated.json()["provenance"]["source_version_id"] == original["version_id"]
        assert updated.json()["provenance"]["import_origin"] == origin
        history = client.get(recipe_path + "/history").json()["history"]
        assert history[1] == original
        assert client.post(path, json=body(raw), headers=headers(csrf, key)).json() == original
        duplicate = client.post(path, json=body(raw), headers=headers(csrf))
        assert (
            duplicate.status_code == 409
            and duplicate.json()["error_code"] == "JSONLD_ALREADY_IMPORTED"
        )
        with session_factory(migrated_engine)() as db:
            record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == key))
            assert record is not None and record.result == {"recipe_id": rid, "version": 1}
            raw_snapshots = json.dumps(db.scalars(select(RecipeVersion.snapshot)).all())
            for discarded in (
                "Discarded-author-value",
                "Discarded-license-value",
                "Discarded-storage-value",
                "discarded.example.org",
                "0 kcal",
            ):
                assert discarded not in raw_snapshots


def test_exact_document_hash_is_scoped_and_different_bytes_are_not_semantic_dedup(
    settings: Settings, migrated_engine: Engine
) -> None:
    raw = document()
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        for hid in (household(client, csrf), household(client, csrf)):
            path = f"/api/v1/households/{hid}/recipe-imports"
            assert client.post(path, json=body(raw), headers=headers(csrf)).status_code == 201
            assert (
                client.post(path, json=body(raw + "\n"), headers=headers(csrf)).status_code == 201
            )
            assert client.post(path, json=body(raw), headers=headers(csrf)).status_code == 409
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(Recipe)) == 4


def test_two_distinct_sessions_create_one_exact_import(
    settings: Settings, migrated_engine: Engine
) -> None:
    app = create_app(settings)
    with TestClient(app) as first, TestClient(app) as second:
        csrf = login(first)
        other_csrf = login(second, register=False)
        hid = household(first, csrf)
        path = f"/api/v1/households/{hid}/recipe-imports"
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(client.post, path, json=body(document()), headers=headers(token))
                for client, token in ((first, csrf), (second, other_csrf))
            ]
            responses = [future.result(timeout=10) for future in futures]
        assert sorted(response.status_code for response in responses) == [201, 409]
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(RecipeVersion)) == 1
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.action == "recipe.jsonld_imported")
                )
                == 1
            )


@pytest.mark.parametrize("case", ["long_ingredient", "oversized_origin"])
def test_previewable_documents_reject_save_atomically_without_truncation(
    case: str, settings: Settings, migrated_engine: Engine
) -> None:
    raw = (
        document(recipeIngredient=["a" * 161])
        if case == "long_ingredient"
        else nested_document(8, 160, 30)
    )
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        path = f"/api/v1/households/{hid}/recipe-imports"
        assert (
            client.post(path + "/preview", json=body(raw), headers=headers(csrf)).status_code == 200
        )
        failure = client.post(path, json=body(raw), headers=headers(csrf))
        assert failure.status_code == 422
        assert failure.json()["error_code"] == (
            "JSONLD_CATALOGUE_LIMIT" if case == "long_ingredient" else "RECIPE_SNAPSHOT_TOO_LARGE"
        )
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(Recipe)) == 0
            assert db.scalar(select(func.count()).select_from(RecipeVersion)) == 0
            assert db.scalar(select(func.count()).select_from(AuditEvent)) == 1
            assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 1


def test_manual_edits_include_immutable_origin_in_whole_snapshot_budget(
    settings: Settings, migrated_engine: Engine
) -> None:
    raw = nested_document(6, 140, 25)
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        imported = client.post(
            f"/api/v1/households/{hid}/recipe-imports", json=body(raw), headers=headers(csrf)
        )
        assert imported.status_code == 201
        path = f"/api/v1/households/{hid}/recipes/{imported.json()['id']}"
        update = edit_input()
        update["instructions"] = ["m" * 400] * 10
        update["ingredients"] = [
            {"name": "s" * 80, "amount": None, "unit": "unknown", "weight_state": "unknown"}
            for _ in range(30)
        ]
        assert len(json.dumps(update).encode()) < 16384
        failure = client.put(path, json=update, headers=headers(csrf))
        assert (
            failure.status_code == 422
            and failure.json()["error_code"] == "RECIPE_SNAPSHOT_TOO_LARGE"
        )
        assert client.get(path).json() == imported.json()
        assert len(client.get(path + "/history").json()["history"]) == 1


def test_late_audit_failure_rolls_back_recipe_version_and_idempotency(
    settings: Settings, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise ApiError(503, "SERVICE_NOT_READY", "Usługa nie jest jeszcze gotowa.")

    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        monkeypatch.setattr(save, "audit", fail)
        assert (
            client.post(
                f"/api/v1/households/{hid}/recipe-imports",
                json=body(document()),
                headers=headers(csrf),
            ).status_code
            == 503
        )
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(RecipeVersion)) == 0
            assert db.scalar(select(func.count()).select_from(Recipe)) == 0
            assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 1


def test_partial_unique_index_and_immutable_origin_work_in_postgres(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        imported = client.post(
            f"/api/v1/households/{hid}/recipe-imports", json=body(document()), headers=headers(csrf)
        ).json()
        actor = UUID(imported["provenance"]["import_origin"]["actor_user_id"])
        with session_factory(migrated_engine)() as db:
            version = db.get(RecipeVersion, UUID(imported["version_id"]))
            assert version is not None
            copied = dict(version.snapshot)
        with pytest.raises(IntegrityError):
            with session_factory(migrated_engine).begin() as db:
                new_recipe(db, UUID(hid), actor, copied)
        for statement in (
            "UPDATE recipe_versions SET snapshot = snapshot || '{}'::jsonb",
            "DELETE FROM recipe_versions",
        ):
            with pytest.raises(IntegrityError):
                with migrated_engine.begin() as connection:
                    connection.execute(text(statement))
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(Recipe)) == 1


def test_legacy_snapshot_is_readable_without_rewriting_immutable_json(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as client:
        csrf = login(client)
        hid = household(client, csrf)
        actor = UUID(client.get("/api/v1/auth/session").json()["user"]["id"])
        legacy = original_snapshots()[0]
        legacy["provenance"].pop("import_origin", None)
        assert RecipeSnapshot.model_validate(legacy).provenance.import_origin is None
        with session_factory(migrated_engine).begin() as db:
            recipe = Recipe(household_id=UUID(hid), current_version=1, created_at=now())
            db.add(recipe)
            db.flush()
            db.add(
                RecipeVersion(
                    recipe_id=recipe.id,
                    household_id=UUID(hid),
                    version=1,
                    created_at=now(),
                    actor_user_id=actor,
                    snapshot=legacy,
                )
            )
            rid = str(recipe.id)
        assert (
            client.get(f"/api/v1/households/{hid}/recipes/{rid}").json()["provenance"][
                "import_origin"
            ]
            is None
        )
        with session_factory(migrated_engine)() as db:
            row = db.scalar(select(RecipeVersion).where(RecipeVersion.recipe_id == UUID(rid)))
            assert row is not None and row.snapshot == legacy


def test_new_index_migration_roundtrip_has_no_metadata_drift(postgres_settings: Settings) -> None:
    assert postgres_settings.database_url is not None
    command.upgrade(migration_config(), "head")
    command.check(migration_config())
    command.downgrade(migration_config(), "0005_recipe_links")
    command.upgrade(migration_config(), "head")
    command.check(migration_config())
