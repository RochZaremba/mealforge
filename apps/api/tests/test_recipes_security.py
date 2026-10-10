"""Independent private catalogue acceptance against isolated PostgreSQL."""

import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mealforge.core.config import Settings
from mealforge.households.models import AuditEvent, HouseholdMember, NutritionProfile
from mealforge.main import create_app
from mealforge.recipes.models import Recipe, RecipeVersion

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:3000"
PASSWORD = "Independent-recipe-QA-password-2026!"
ClientFactory = Callable[[], TestClient]


@pytest.fixture
def recipe_app(postgres_settings: Settings, migrated_engine: Engine) -> FastAPI:
    assert migrated_engine is not None
    return create_app(
        Settings(
            database_url=postgres_settings.database_url,
            session_secret=SecretStr("QA-recipes-session-secret-" + "x" * 40),
            trusted_origins=(ORIGIN,),
            app_env="test",
        )
    )


@pytest.fixture
def clients(recipe_app: FastAPI) -> Iterator[ClientFactory]:
    with ExitStack() as stack:
        yield lambda: stack.enter_context(TestClient(recipe_app))


def account(clients: ClientFactory) -> TestClient:
    client = clients()
    email = f"recipe-{uuid4().hex}@example.invalid"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": "Autor QA",
        },
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 201
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": PASSWORD,
            },
            headers={"Origin": ORIGIN},
        ).status_code
        == 200
    )
    return client


def headers(client: TestClient, key: str | None = None) -> dict[str, str]:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 200
    return {
        "Origin": ORIGIN,
        "X-CSRF-Token": response.json()["csrf_token"],
        "Idempotency-Key": key or str(uuid4()),
    }


def household(client: TestClient) -> str:
    created = client.post(
        "/api/v1/households", json={"name": "Realny dom QA"}, headers=headers(client)
    )
    assert created.status_code == 201
    return created.json()["id"]


def path(household_id: str, recipe_id: str | None = None) -> str:
    base = f"/api/v1/households/{household_id}/recipes"
    return f"{base}/{recipe_id}" if recipe_id else base


def payload() -> dict:
    return {
        "title": "Własny przepis QA",
        "instructions": ["Odważ składniki.", "Wymieszaj."],
        "ingredients": [
            {"name": "Warzywo", "amount": "125.001", "unit": "g", "weight_state": "raw"},
            {"name": "Płyn", "amount": None, "unit": "ml", "weight_state": "unknown"},
        ],
        "rights_attestation": "i_am_author",
    }


def create(client: TestClient, household_id: str, key: str | None = None) -> dict:
    response = client.post(path(household_id), json=payload(), headers=headers(client, key))
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def demo(client: TestClient, key: str | None = None) -> dict:
    response = client.post(
        "/api/v1/households/demo",
        json={"confirmation": "create_separate_demo"},
        headers=headers(client, key),
    )
    assert response.status_code == 201
    return response.json()["household"]


def linked_account(
    owner: TestClient, household_id: str, clients: ClientFactory, role: str = "viewer"
) -> tuple[TestClient, dict]:
    recipient = account(clients)
    invited = owner.post(
        f"/api/v1/households/{household_id}/invite",
        json={"role": role, "member_id": None},
        headers=headers(owner),
    )
    assert invited.status_code == 201
    accepted = recipient.post(
        "/api/v1/household-invitations/accept",
        json={"token": invited.json()["token"]},
        headers=headers(recipient),
    )
    assert accepted.status_code == 200
    return recipient, accepted.json()["member"]


def counts(engine: Engine) -> tuple[int, int, int]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0
            for model in (Recipe, RecipeVersion, AuditEvent)
        )


def assert_unknown(recipe: dict) -> None:
    assert recipe["status"] == "draft_requires_review"
    assert recipe["planner_eligible"] is False
    assert recipe["nutrients"] == dict.fromkeys(
        ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]
    )
    assert recipe["allergen_status"] == "unknown"
    for field in [
        "yield_mass_g",
        "prep_time_minutes",
        "cook_time_minutes",
        "storage_method",
        "storage_validation_ref",
        "prices",
    ]:
        assert recipe[field] is None
    assert recipe["warnings"]


def test_recipe_amounts_remain_exact_and_unknowns_never_become_zero(clients: ClientFactory) -> None:
    owner = account(clients)
    hid = household(owner)
    submitted = payload()
    submitted["ingredients"] += [
        {"name": "Opakowanie", "amount": 2, "unit": "piece", "weight_state": "as_packaged"},
        {
            "name": "Jednostka nieznana",
            "amount": "1.250",
            "unit": "unknown",
            "weight_state": "cooked",
        },
    ]
    response = owner.post(path(hid), json=submitted, headers=headers(owner))
    assert response.status_code == 201
    recipe = response.json()
    assert [item["amount"] for item in recipe["ingredients"]] == ["125.001", None, "2", "1.25"]
    assert [item["unit"] for item in recipe["ingredients"]] == ["g", "ml", "piece", "unknown"]
    assert [item["weight_state"] for item in recipe["ingredients"]] == [
        "raw",
        "unknown",
        "as_packaged",
        "cooked",
    ]
    assert_unknown(recipe)
    assert recipe["servings"] is None
    assert owner.get(path(hid, recipe["id"])).json() == recipe


@pytest.mark.parametrize(
    "amount",
    [0, "0.000", -1, "-0.001", 1.25, True, False, "1.0001", "1000000", "NaN", "1e2", "2\n"],
)
def test_invalid_ingredient_amount_does_not_write_or_audit(
    clients: ClientFactory,
    migrated_engine: Engine,
    amount: object,
) -> None:
    owner = account(clients)
    hid = household(owner)
    before = counts(migrated_engine)
    submitted = payload()
    submitted["ingredients"][0]["amount"] = amount
    denied = owner.post(path(hid), json=submitted, headers=headers(owner))
    assert denied.status_code == 422
    assert counts(migrated_engine) == before


def test_server_controlled_recipe_claims_cannot_be_injected(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    before = counts(migrated_engine)
    for field, value in {
        "license": "CC0-1.0",
        "provenance": {"author": "MealForge"},
        "source_url": "http://127.0.0.1/secret",
        "planner_eligible": True,
        "status": "validated",
        "allergen_status": "safe",
        "yield_mass_g": "400",
        "storage_method": "shelf_stable",
        "storage_validation_ref": "invented",
        "nutrients": {"kcal": "500"},
    }.items():
        submitted = payload()
        submitted[field] = value
        assert owner.post(path(hid), json=submitted, headers=headers(owner)).status_code == 422
    for field in ["nutrients_per_100g", "allergen_status", "license", "normalized_ingredient_id"]:
        submitted = payload()
        submitted["ingredients"][0][field] = "untrusted"
        assert owner.post(path(hid), json=submitted, headers=headers(owner)).status_code == 422
    submitted = payload()
    del submitted["rights_attestation"]
    assert owner.post(path(hid), json=submitted, headers=headers(owner)).status_code == 422
    assert counts(migrated_engine) == before


def test_private_recipe_reads_and_mutations_deny_foreign_households(clients: ClientFactory) -> None:
    owner, foreign = account(clients), account(clients)
    hid, foreign_hid = household(owner), household(foreign)
    recipe = create(owner, hid)
    for url in [
        path(hid),
        path(hid, recipe["id"]),
        path(hid, recipe["id"]) + "/history",
        path(foreign_hid, recipe["id"]),
        path(foreign_hid, recipe["id"]) + "/history",
    ]:
        assert foreign.get(url).status_code == 404
    assert foreign.post(path(hid), json=payload(), headers=headers(foreign)).status_code == 404
    body = {**payload(), "expected_version": 1}
    assert (
        foreign.put(path(hid, recipe["id"]), json=body, headers=headers(foreign)).status_code == 404
    )
    assert owner.get(path(hid, recipe["id"])).json() == recipe


def test_viewer_reads_but_cannot_write_and_revocation_invalidates_replays(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    recipe = create(owner, hid)
    viewer, _ = linked_account(owner, hid, clients)
    for url in [path(hid), path(hid, recipe["id"]), path(hid, recipe["id"]) + "/history"]:
        assert viewer.get(url).status_code == 200
    assert viewer.post(path(hid), json=payload(), headers=headers(viewer)).status_code == 403
    assert (
        viewer.put(
            path(hid, recipe["id"]),
            json={**payload(), "expected_version": 1},
            headers=headers(viewer),
        ).status_code
        == 403
    )
    editor, membership = linked_account(owner, hid, clients, "editor")
    key = str(uuid4())
    created = create(editor, hid, key)
    assert (
        owner.put(
            f"/api/v1/households/{hid}/members/{membership['id']}/access",
            json={
                "expected_version": membership["access_version"],
                "role": "editor",
                "access_enabled": False,
            },
            headers=headers(owner),
        ).status_code
        == 200
    )
    before = counts(migrated_engine)
    for url in [path(hid), path(hid, created["id"]), path(hid, created["id"]) + "/history"]:
        assert editor.get(url).status_code == 404
    assert editor.post(path(hid), json=payload(), headers=headers(editor, key)).status_code == 404
    assert counts(migrated_engine) == before


def test_auth_csrf_origin_and_idempotency_conflicts_preserve_recipe_history(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    assert clients().get(path(hid)).status_code == 401
    before = counts(migrated_engine)
    for field, value in [("Origin", "https://evil.example"), ("X-CSRF-Token", "bad")]:
        incoming = headers(owner)
        incoming[field] = value
        assert owner.post(path(hid), json=payload(), headers=incoming).status_code == 403
    assert counts(migrated_engine) == before
    key = str(uuid4())
    created = create(owner, hid, key)
    assert create(owner, hid, key) == created
    changed = payload()
    changed["title"] = "Zmiana pod tym samym kluczem"
    assert owner.post(path(hid), json=changed, headers=headers(owner, key)).status_code == 409
    assert counts(migrated_engine) == (before[0] + 1, before[1] + 1, before[2] + 1)


def test_distinct_editor_sessions_race_one_expected_version_exactly_once(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    recipe = create(owner, hid)
    editor, _ = linked_account(owner, hid, clients, "editor")
    actors = [owner, editor]
    incoming = [headers(actor) for actor in actors]
    gate = Barrier(2)
    before = counts(migrated_engine)

    def save(index: int) -> int:
        submitted = {**payload(), "expected_version": 1, "instructions": [f"Wkład autora {index}."]}
        gate.wait(timeout=10)
        return (
            actors[index]
            .put(path(hid, recipe["id"]), json=submitted, headers=incoming[index])
            .status_code
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, [0, 1]))
    assert sorted(results) == [200, 409]
    history = owner.get(path(hid, recipe["id"]) + "/history").json()["history"]
    assert [entry["version"] for entry in history] == [2, 1]
    assert history[1] == recipe
    assert history[0]["instructions"] == [f"Wkład autora {results.index(200)}."]
    assert counts(migrated_engine) == (before[0], before[1] + 1, before[2] + 1)


def test_actual_database_guards_immutable_versions_and_current_reference(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    recipe = create(owner, hid)
    for statement in [
        "UPDATE recipe_versions SET snapshot='{}'::jsonb WHERE id=:id",
        "DELETE FROM recipe_versions WHERE id=:id",
    ]:
        with pytest.raises(IntegrityError), migrated_engine.begin() as connection:
            connection.execute(text(statement), {"id": UUID(recipe["version_id"])})
    with pytest.raises(IntegrityError), migrated_engine.begin() as connection:
        connection.execute(
            update(Recipe).where(Recipe.id == UUID(recipe["id"])).values(current_version=999)
        )
    assert owner.get(path(hid, recipe["id"])).json() == recipe


def test_recipe_history_and_list_pagination_reach_every_version_with_bounds(
    clients: ClientFactory,
) -> None:
    owner = account(clients)
    hid = household(owner)
    created = [create(owner, hid) for _ in range(3)]
    cursor = None
    found = []
    while True:
        response = owner.get(
            path(hid), params={"limit": 1, **({"after": cursor} if cursor else {})}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recipes"]) <= 1
        assert all(
            "instructions" not in entry and "ingredients" not in entry for entry in data["recipes"]
        )
        found.extend(entry["id"] for entry in data["recipes"])
        cursor = data["next_cursor"]
        if cursor is None:
            break
        assert len(found) <= 3
    assert set(found) == {entry["id"] for entry in created}
    assert len(found) == 3
    rid = created[0]["id"]
    for version in range(1, 7):
        assert (
            owner.put(
                path(hid, rid),
                json={
                    **payload(),
                    "expected_version": version,
                    "instructions": [f"Wersja {version + 1}"],
                },
                headers=headers(owner),
            ).status_code
            == 200
        )
    before_version = None
    versions = []
    while True:
        response = owner.get(
            path(hid, rid) + "/history",
            params={"limit": 2, **({"before_version": before_version} if before_version else {})},
        )
        assert response.status_code == 200
        assert len(response.content) < 262144
        data = response.json()
        assert len(data["history"]) <= 2
        versions.extend(entry["version"] for entry in data["history"])
        before_version = data["next_before_version"]
        if before_version is None:
            break
        assert len(versions) <= 7
    assert versions == [7, 6, 5, 4, 3, 2, 1]
    assert owner.get(path(hid), params={"limit": 21}).status_code == 422
    assert owner.get(path(hid), params={"after": "not-a-uuid"}).status_code == 422
    assert owner.get(path(hid, rid) + "/history", params={"limit": 6}).status_code == 422
    assert owner.get(path(hid, rid) + "/history", params={"before_version": 0}).status_code == 422


def test_utf8_actual_body_budget_rejects_without_partial_recipe(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = household(owner)
    submitted = payload()
    submitted["instructions"] = ["ż" * 500 for _ in range(30)]
    encoded = json.dumps(submitted, ensure_ascii=False).encode()
    assert len(encoded) > 16384
    before = counts(migrated_engine)
    response = owner.post(
        path(hid), content=encoded, headers={**headers(owner), "Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert counts(migrated_engine) == before


def profile_rows(engine: Engine) -> list[tuple]:
    with Session(engine) as session:
        profiles = session.scalars(select(NutritionProfile).order_by(NutritionProfile.id)).all()
        return [
            tuple(getattr(profile, column.name) for column in NutritionProfile.__table__.columns)
            for profile in profiles
        ]


def test_demo_is_explicit_separate_idempotent_and_preserves_all_real_target_columns(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    assert owner.get("/api/v1/households").json()["households"] == []
    real_id = household(owner)
    members = owner.get(f"/api/v1/households/{real_id}/members").json()["members"]
    real_member = members[0]["id"]
    for revision, calories in enumerate(["2700.125", "2810.375"]):
        saved = owner.put(
            f"/api/v1/households/{real_id}/members/{real_member}/nutrition-target",
            json={
                "expected_version": revision,
                "kcal_target": calories,
                "protein_target_g": "0",
                "carbs_target_g": None,
                "fat_target_g": "1.234",
                "goal_type": "custom",
                "valid_from": datetime.now(ZoneInfo("Europe/Warsaw")).date().isoformat(),
            },
            headers=headers(owner),
        )
        assert saved.status_code == 200
    before = profile_rows(migrated_engine)
    original_history = owner.get(
        f"/api/v1/households/{real_id}/members/{real_member}/nutrition-target/history"
    ).json()
    assert owner.get(path(real_id)).json()["recipes"] == []
    for submitted in [{}, {"confirmation": "yes"}, {"confirmation": True}]:
        assert (
            owner.post(
                "/api/v1/households/demo", json=submitted, headers=headers(owner)
            ).status_code
            == 422
        )
    assert len(owner.get("/api/v1/households").json()["households"]) == 1
    key = str(uuid4())
    seeded = demo(owner, key)
    assert seeded["id"] != real_id
    assert seeded["source"] == "demo_seed"
    assert demo(owner, key) == seeded
    assert len(owner.get("/api/v1/households").json()["households"]) == 2
    assert owner.get(path(real_id)).json()["recipes"] == []
    seeded_members = owner.get(f"/api/v1/households/{seeded['id']}/members").json()["members"]
    assert len(seeded_members) == 2
    assert sorted(
        Decimal(member["nutrition_target"]["kcal_target"]) for member in seeded_members
    ) == [Decimal("1600"), Decimal("2700")]
    for member in seeded_members:
        target = member["nutrition_target"]
        assert target["source"] == "demo_seed"
        assert target["version"] == 1
        assert all(
            target[field] is None
            for field in ["protein_target_g", "carbs_target_g", "fat_target_g"]
        )
    assert (
        len(owner.get(f"/api/v1/households/{seeded['id']}/meal-slot-presets").json()["slots"]) == 5
    )
    assert (
        owner.get(
            f"/api/v1/households/{real_id}/members/{real_member}/nutrition-target/history"
        ).json()
        == original_history
    )
    real_profile_ids = {row[0] for row in before}
    assert [row for row in profile_rows(migrated_engine) if row[0] in real_profile_ids] == before


def test_demo_original_fixture_exact_amounts_unknowns_and_private_edit_lineage(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = demo(owner)["id"]
    fixture = json.loads(
        (Path(__file__).resolve().parents[3] / "fixtures/original-recipes.json").read_text()
    )["recipes"]
    originals = {entry["id"]: entry for entry in fixture}
    summaries = owner.get(path(hid)).json()["recipes"]
    assert len(summaries) == 3
    amount_count = 0
    for summary in summaries:
        recipe = owner.get(path(hid, summary["id"])).json()
        assert_unknown(recipe)
        assert recipe["servings"] == 2
        assert recipe["servings_basis"] == "intentional_recipe_design"
        provenance = recipe["provenance"]
        original = originals[provenance["original_origin"]["fixture_id"]]
        assert provenance["source_id"] == "original_fixture"
        assert provenance["author"] == "MealForge"
        assert provenance["license"] == "CC0-1.0"
        assert provenance["license_scope"] == "original_recipe_text"
        assert provenance["source_version_id"] is None
        assert recipe["instructions"] == original["instructions"]
        assert [
            (item["name"], item["amount"], item["unit"], item["weight_state"])
            for item in recipe["ingredients"]
        ] == [
            (item["raw_name"], item["amount"], item["unit"], item["raw_or_cooked"])
            for item in original["ingredients"]
        ]
        amount_count += len(recipe["ingredients"])
        for item in recipe["ingredients"]:
            assert item["nutrients_per_100g"] == dict.fromkeys(
                ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]
            )
            assert item["nutrient_provenance"] is None
            assert item["allergen_status"] == "unknown"
        with Session(migrated_engine) as session:
            stored = session.get(RecipeVersion, UUID(recipe["version_id"]))
            assert stored is not None
            assert stored.snapshot["ingredients"] == recipe["ingredients"]
    assert amount_count == 13
    original_detail = owner.get(path(hid, summaries[0]["id"])).json()
    submitted = {
        "title": original_detail["title"],
        "ingredients": [
            {key: item[key] for key in ["name", "amount", "unit", "weight_state"]}
            for item in original_detail["ingredients"]
        ],
        "instructions": ["Mój własny dodatkowy opis."],
        "rights_attestation": "i_am_author",
        "expected_version": 1,
    }
    edited = owner.put(path(hid, original_detail["id"]), json=submitted, headers=headers(owner))
    assert edited.status_code == 200
    revised = edited.json()
    assert_unknown(revised)
    assert revised["provenance"]["source_id"] == "private_user_content"
    assert revised["provenance"]["license"] is None
    assert revised["provenance"]["license_scope"] is None
    assert revised["provenance"]["rights_attestation"] == "i_am_author"
    assert revised["provenance"]["source_version_id"] == original_detail["version_id"]
    assert (
        revised["provenance"]["original_origin"] == original_detail["provenance"]["original_origin"]
    )
    history = owner.get(path(hid, original_detail["id"]) + "/history").json()["history"]
    assert history == [revised, original_detail]
    submitted["expected_version"] = 2
    submitted["instructions"] = ["Drugi wkład autora."]
    second = owner.put(path(hid, original_detail["id"]), json=submitted, headers=headers(owner))
    assert second.status_code == 200
    assert second.json()["provenance"]["source_version_id"] == revised["version_id"]
    assert (
        owner.get(path(hid, original_detail["id"]) + "/history").json()["history"][2]
        == original_detail
    )


def test_demo_create_replay_rechecks_current_owner_membership_and_any_account_can_opt_in(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    real_hid = household(owner)
    viewer, _ = linked_account(owner, real_hid, clients)
    key = str(uuid4())
    seeded = demo(viewer, key)
    assert seeded["role"] == "owner"
    user_id = viewer.get("/api/v1/auth/session").json()["user"]["id"]
    with migrated_engine.begin() as connection:
        connection.execute(
            update(HouseholdMember)
            .where(
                HouseholdMember.household_id == UUID(seeded["id"]),
                HouseholdMember.user_id == UUID(user_id),
            )
            .values(access_enabled=False, access_version=1)
        )
    before = counts(migrated_engine)
    replay = viewer.post(
        "/api/v1/households/demo",
        json={"confirmation": "create_separate_demo"},
        headers=headers(viewer, key),
    )
    assert replay.status_code == 404
    assert counts(migrated_engine) == before
    assert seeded["id"] not in {
        item["id"] for item in viewer.get("/api/v1/households").json()["households"]
    }


def test_same_account_distinct_sessions_concurrent_demo_key_create_only_one_demo(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    first = account(clients)
    email = first.get("/api/v1/auth/session").json()["user"]["email"]
    second = clients()
    assert (
        second.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            headers={"Origin": ORIGIN},
        ).status_code
        == 200
    )
    key = str(uuid4())
    actors = [first, second]
    incoming = [headers(actor, key) for actor in actors]
    gate = Barrier(2)

    def seed(index: int) -> dict:
        gate.wait(timeout=10)
        response = actors[index].post(
            "/api/v1/households/demo",
            json={"confirmation": "create_separate_demo"},
            headers=incoming[index],
        )
        assert response.status_code == 201
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(seed, [0, 1]))
    assert result[0] == result[1]
    assert len(first.get("/api/v1/households").json()["households"]) == 1
    assert counts(migrated_engine)[:2] == (3, 3)
    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(HouseholdMember)) == 2
        assert session.scalar(select(func.count()).select_from(NutritionProfile)) == 2
