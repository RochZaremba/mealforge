"""Independent JSON-LD save acceptance on isolated, migrated PostgreSQL."""

import copy
import json
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_onboarding import target
from test_recipe_links_security import ORIGIN, PASSWORD, account, headers, home, linked
from test_recipe_links_security import clients as clients

from mealforge.households.models import AuditEvent, IdempotencyRecord
from mealforge.importers.jsonld import parse_own_jsonld
from mealforge.recipes.models import Recipe, RecipeVersion

pytestmark = pytest.mark.integration


def document(**updates):
    return json.dumps(
        {
            "@context": "https://127.0.0.1/private-context",
            "@type": "Recipe",
            "name": "Własna receptura importowana QA",
            "recipeIngredient": ["3 łyżki mąki", "woda według potrzeby"],
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Przygotowanie QA",
                    "itemListElement": [{"@type": "HowToStep", "text": "Połącz składniki."}],
                }
            ],
            "recipeYield": ["3 kg 700 g", "4 porcje"],
            "nutrition": {"calories": "0 kcal"},
            "license": "CC0-source-sentinel",
            "author": "Unverified-author-sentinel",
            "image": "http://169.254.169.254/private-image",
            "storageMethod": "shelf-stable-source-sentinel",
            **updates,
        },
        ensure_ascii=False,
    )


def route(hid):
    return f"/api/v1/households/{hid}/recipe-imports"


def body(raw=None):
    return {"document": raw or document(), "rights_attestation": "i_am_author"}


def save(client, hid, raw=None, key=None):
    response = client.post(route(hid), json=body(raw), headers=headers(client, key))
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def snapshots(engine, tables):
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"SELECT row_to_json(t)::text FROM {table} AS t ORDER BY id")
            )
            .scalars()
            .all()
            for table in tables
        }


def write_counts(engine):
    with Session(engine) as db:
        return tuple(
            db.scalar(select(func.count()).select_from(model))
            for model in (Recipe, RecipeVersion, AuditEvent, IdempotencyRecord)
        )


def unknown(recipe):
    assert recipe["status"] == "draft_requires_review"
    assert recipe["planner_eligible"] is False
    assert recipe["allergen_status"] == "unknown"
    assert all(value is None for value in recipe["nutrients"].values())
    for field in (
        "yield_mass_g",
        "servings",
        "prep_time_minutes",
        "cook_time_minutes",
        "storage_method",
        "storage_validation_ref",
        "prices",
    ):
        assert recipe[field] is None
    assert recipe["yield_basis"] == "unknown_until_weighed"
    assert recipe["servings_basis"] == "unknown"
    for ingredient in recipe["ingredients"]:
        assert ingredient["amount"] is None
        assert ingredient["unit"] == ingredient["weight_state"] == "unknown"
        assert ingredient["allergen_status"] == "unknown"
        assert all(value is None for value in ingredient["nutrients_per_100g"].values())
        assert ingredient["nutrient_provenance"] is None


def test_saved_origin_unknowns_no_network_and_private_metadata_preserve_profiles(
    clients, migrated_engine, monkeypatch, caplog
):
    owner = account(clients)
    hid = home(owner)
    members = owner.get(f"/api/v1/households/{hid}/members").json()["members"]
    assert (
        owner.put(
            f"/api/v1/households/{hid}/members/{members[0]['id']}/nutrition-target",
            json=target(kcal_target="2700.125", protein_target_g="0", fat_target_g="1.234"),
            headers=headers(owner),
        ).status_code
        == 200
    )
    protected = snapshots(
        migrated_engine, ("nutrition_profiles", "household_members", "recipe_links")
    )
    raw = document()
    auth_headers = headers(owner)
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append("outbound")
        raise AssertionError("Save attempted outbound I/O")

    original_dns = socket.getaddrinfo

    def dns(host, *args, **kwargs):
        if host not in ("localhost", "127.0.0.1", "::1"):
            return forbidden()
        return original_dns(host, *args, **kwargs)

    original_send = httpx.Client.send

    def local_send(client, request, *args, **kwargs):
        if request.url.host != "testserver":
            return forbidden()
        return original_send(client, request, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(httpx.Client, "send", local_send)
    response = owner.post(route(hid), json=body(raw), headers=auth_headers)
    assert response.status_code == 201
    recipe = response.json()
    unknown(recipe)
    provenance = recipe["provenance"]
    assert provenance["source_mode"] == "user_supplied_jsonld"
    assert provenance["source_id"] == "private_user_content"
    assert provenance["license"] is provenance["license_scope"] is None
    origin = provenance["import_origin"]
    assert set(origin) == {
        "source_sha256",
        "parser_version",
        "actor_user_id",
        "imported_at",
        "ingredients",
        "instructions",
        "recipe_yield_raw",
        "ignored_source_fields",
    }
    assert origin["source_sha256"] == sha256(raw.encode()).hexdigest()
    assert origin["parser_version"] == "jsonld-preview-v1"
    assert origin["actor_user_id"] == owner.get("/api/v1/auth/session").json()["user"]["id"]
    assert origin["ingredients"] == ["3 łyżki mąki", "woda według potrzeby"]
    assert origin["instructions"] == [
        {"text": "Połącz składniki.", "section_path": ["Przygotowanie QA"]}
    ]
    assert origin["recipe_yield_raw"] == ["3 kg 700 g", "4 porcje"]
    assert {"nutrition", "license", "author", "storageMethod", "image"} <= set(
        origin["ignored_source_fields"]
    )
    assert protected == snapshots(migrated_engine, tuple(protected))
    assert attempts == []
    with Session(migrated_engine) as db:
        version = db.scalar(
            select(RecipeVersion).where(RecipeVersion.id == UUID(recipe["version_id"]))
        )
        assert version is not None
        serialized = json.dumps(version.snapshot)
        assert raw not in serialized
        for sentinel in (
            "CC0-source-sentinel",
            "Unverified-author-sentinel",
            "private-image",
            "shelf-stable-source-sentinel",
        ):
            assert sentinel not in serialized
            assert sentinel not in caplog.text
        record = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.key == auth_headers["Idempotency-Key"]
            )
        )
        assert record is not None
        assert "document" not in record.result and "ingredients" not in record.result
        assert raw not in json.dumps(record.result)
    metadata = snapshots(migrated_engine, ("audit_events", "idempotency_records"))
    assert raw not in json.dumps(metadata)
    assert "Połącz składniki." not in json.dumps(metadata)


def test_dedup_replay_original_version_after_edit_and_lineage_remain_immutable(
    clients, migrated_engine
):
    owner = account(clients)
    hid = home(owner)
    raw = document()
    key = str(uuid4())
    initial = save(owner, hid, raw, key)
    first_snapshot = snapshots(migrated_engine, ("recipe_versions",))["recipe_versions"][0]
    changed = owner.put(
        f"/api/v1/households/{hid}/recipes/{initial['id']}",
        headers=headers(owner),
        json={
            "expected_version": 1,
            "title": "Ręczna nowa wersja QA",
            "instructions": ["Ręcznie zmieniony krok."],
            "ingredients": [
                {"name": "mąka", "amount": "125.125", "unit": "g", "weight_state": "raw"}
            ],
            "rights_attestation": "i_am_author",
        },
    )
    assert changed.status_code == 200
    current = changed.json()
    assert current["provenance"]["source_mode"] == "user_authored"
    assert current["provenance"]["source_version_id"] == initial["version_id"]
    assert current["provenance"]["import_origin"] == initial["provenance"]["import_origin"]
    before = write_counts(migrated_engine)
    assert save(owner, hid, raw, key) == initial
    changed_request = owner.post(
        route(hid),
        json=body(document(name="Different request with same key")),
        headers=headers(owner, key),
    )
    assert changed_request.status_code == 409
    assert changed_request.json()["error_code"] == "IDEMPOTENCY_CONFLICT"
    duplicate = owner.post(route(hid), json=body(raw), headers=headers(owner))
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "JSONLD_ALREADY_IMPORTED"
    assert write_counts(migrated_engine) == before
    history = owner.get(f"/api/v1/households/{hid}/recipes/{initial['id']}/history").json()[
        "history"
    ]
    assert history == [current, initial]
    assert first_snapshot in snapshots(migrated_engine, ("recipe_versions",))["recipe_versions"]
    # Byte-identical documents may be saved in a separate authorized household.
    second_hid = home(owner)
    separate = save(owner, second_hid, raw)
    assert separate["id"] != initial["id"]
    assert separate["household_id"] == second_hid


def test_current_role_revocation_idor_csrf_and_idempotency_auth(clients, migrated_engine):
    owner = account(clients)
    hid = home(owner)
    editor, member = linked(owner, hid, clients, "editor")
    outsider = account(clients)
    key = str(uuid4())
    saved = save(editor, hid, key=key)
    before = write_counts(migrated_engine)
    assert outsider.post(route(hid), json=body(), headers=headers(outsider)).status_code == 404
    assert owner.post(route(uuid4()), json=body(), headers=headers(owner)).status_code == 404
    assert clients().post(route(hid), json=body()).status_code == 401
    valid = headers(owner)
    for bad in (
        {**valid, "Origin": "https://attacker.invalid"},
        {key: value for key, value in valid.items() if key != "Origin"},
        {**valid, "X-CSRF-Token": "invalid"},
        {key: value for key, value in valid.items() if key != "Idempotency-Key"},
    ):
        assert owner.post(route(hid), json=body(), headers=bad).status_code in (400, 403, 422)
    downgraded = owner.put(
        f"/api/v1/households/{hid}/members/{member['id']}/access",
        headers=headers(owner),
        json={
            "expected_version": member["access_version"],
            "role": "viewer",
            "access_enabled": True,
        },
    )
    assert downgraded.status_code == 200
    assert editor.post(route(hid), json=body(), headers=headers(editor, key)).status_code == 403
    assert (
        editor.post(
            route(hid), json=body(document(name="Nowy dokument")), headers=headers(editor)
        ).status_code
        == 403
    )
    assert editor.get(f"/api/v1/households/{hid}/recipes/{saved['id']}").status_code == 200
    revoked = owner.put(
        f"/api/v1/households/{hid}/members/{member['id']}/access",
        headers=headers(owner),
        json={
            "expected_version": downgraded.json()["access_version"],
            "role": "viewer",
            "access_enabled": False,
        },
    )
    assert revoked.status_code == 200
    assert editor.post(route(hid), json=body(), headers=headers(editor, key)).status_code == 404
    assert editor.get(f"/api/v1/households/{hid}/recipes/{saved['id']}").status_code == 404
    after = write_counts(migrated_engine)
    assert after[:2] == before[:2]
    assert after[2:] == (before[2] + 2, before[3] + 2)


@pytest.mark.parametrize(
    "extra",
    [
        {"provenance": {"import_origin": {"source_sha256": "a" * 64}}},
        {"preview": {"title": "spoofed"}},
        {"nutrients": {"kcal": 0}},
        {"license": "CC0"},
        {"planner_eligible": True},
        {"storage_method": "shelf_stable"},
        {"rights_attestation": "licensed"},
        {"rights_attestation": None},
        {"document": True},
    ],
)
def test_protected_client_fields_cannot_be_saved(clients, migrated_engine, extra):
    owner = account(clients)
    hid = home(owner)
    before = write_counts(migrated_engine)
    assert (
        owner.post(route(hid), json={**body(), **extra}, headers=headers(owner)).status_code == 422
    )
    assert write_counts(migrated_engine) == before


def test_catalogue_limit_and_complete_utf8_snapshot_budget_are_atomic(clients, migrated_engine):
    owner = account(clients)
    hid = home(owner)
    before = write_counts(migrated_engine)
    too_long = document(recipeIngredient=["x" * 161])
    assert (
        owner.post(route(hid) + "/preview", json=body(too_long), headers=headers(owner)).status_code
        == 200
    )
    rejected = owner.post(route(hid), json=body(too_long), headers=headers(owner))
    assert rejected.status_code == 422
    assert rejected.json()["error_code"] == "JSONLD_CATALOGUE_LIMIT"
    # Raw input remains valid and bounded, but the duplicated typed origin +
    # all ingredient metadata exceeds the complete UTF-8 snapshot budget.
    oversized = document(
        recipeIngredient=["ą" * 75] * 40,
        recipeInstructions=["ą" * 85] * 30,
    )
    assert len(oversized.encode()) <= 12288
    assert parse_own_jsonld(oversized).ingredients
    rejected = owner.post(route(hid), json=body(oversized), headers=headers(owner))
    assert rejected.status_code == 422
    assert rejected.json()["error_code"] == "RECIPE_SNAPSHOT_TOO_LARGE"
    malformed = owner.post(route(hid), json=body('{"x":NaN}'), headers=headers(owner))
    assert malformed.status_code == 422
    assert malformed.json()["error_code"] == "JSONLD_INVALID"
    too_many_bytes = owner.post(
        route(hid),
        content=json.dumps(body("x" * 17000)),
        headers={**headers(owner), "Content-Type": "application/json"},
    )
    assert too_many_bytes.status_code == 413
    assert write_counts(migrated_engine) == before


def test_distinct_sessions_concurrent_same_document_commit_once(clients, migrated_engine):
    owner = account(clients)
    hid = home(owner)
    second = clients()
    user = owner.get("/api/v1/auth/session").json()["user"]
    assert (
        second.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": PASSWORD},
            headers={"Origin": ORIGIN},
        ).status_code
        == 200
    )
    auth = [headers(owner), headers(second)]
    assert owner.cookies["mealforge_session"] != second.cookies["mealforge_session"]
    baseline = write_counts(migrated_engine)
    barrier = Barrier(2)

    def submit(index):
        barrier.wait(timeout=10)
        return (owner, second)[index].post(route(hid), json=body(), headers=auth[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, (0, 1)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    rejected = next(response for response in responses if response.status_code == 409)
    assert rejected.json()["error_code"] == "JSONLD_ALREADY_IMPORTED"
    after = write_counts(migrated_engine)
    assert after == tuple(value + 1 for value in baseline)


def test_import_snapshot_cannot_be_rewritten_or_deleted(clients, migrated_engine):
    owner = account(clients)
    hid = home(owner)
    saved = save(owner, hid)
    before = copy.deepcopy(saved)
    for statement in (
        "UPDATE recipe_versions "
        "SET snapshot = jsonb_set(snapshot, '{title}', '\"spoofed\"') WHERE id=:id",
        "DELETE FROM recipe_versions WHERE id=:id",
    ):
        with pytest.raises(IntegrityError):
            with migrated_engine.begin() as db:
                db.execute(text(statement), {"id": UUID(saved["version_id"])})
    assert owner.get(f"/api/v1/households/{hid}/recipes/{saved['id']}").json() == before
