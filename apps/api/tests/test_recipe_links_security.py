"""Independent link-only acceptance using live isolated PostgreSQL and outbound spies."""

import copy
import json
import socket
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from threading import Barrier
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mealforge.core.config import Settings
from mealforge.households.models import AuditEvent, IdempotencyRecord, NutritionProfile
from mealforge.main import create_app
from mealforge.recipes.links.models import RecipeLink
from mealforge.recipes.models import Recipe, RecipeVersion

pytestmark = pytest.mark.integration
ORIGIN = "http://localhost:3000"
PASSWORD = "Link-only-independent-QA-password-2026!"
ClientFactory = Callable[[], TestClient]


@pytest.fixture
def clients(postgres_settings: Settings, migrated_engine: Engine) -> Iterator[ClientFactory]:
    assert migrated_engine is not None
    app: FastAPI = create_app(
        Settings(
            database_url=postgres_settings.database_url,
            session_secret=SecretStr("QA-links-secret-" + "x" * 50),
            trusted_origins=(ORIGIN,),
            app_env="test",
        )
    )
    with ExitStack() as stack:
        yield lambda: stack.enter_context(TestClient(app))


def account(clients: ClientFactory) -> TestClient:
    client = clients()
    email = f"links-{uuid4().hex}@example.invalid"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": "Autor linku QA",
        },
        headers={"Origin": ORIGIN},
    )
    assert registered.status_code == 201
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            headers={"Origin": ORIGIN},
        ).status_code
        == 200
    )
    return client


def headers(client: TestClient, key: str | None = None) -> dict[str, str]:
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    return {
        "Origin": ORIGIN,
        "X-CSRF-Token": session.json()["csrf_token"],
        "Idempotency-Key": key or str(uuid4()),
    }


def home(client: TestClient) -> str:
    created = client.post(
        "/api/v1/households", json={"name": "Prywatne linki QA"}, headers=headers(client)
    )
    assert created.status_code == 201
    return created.json()["id"]


def path(hid: str, lid: str | None = None) -> str:
    result = f"/api/v1/households/{hid}/recipe-links"
    return f"{result}/{lid}" if lid else result


def payload(url: str = "https://aniagotuje.pl/przepis/pomysl#skladniki") -> dict:
    return {
        "user_title": "Moja własna nazwa",
        "source_url": url,
        "own_note": "0 kcal, bez glutenu, pasteryzowane — wyłącznie moja notatka",
        "own_contribution_attestation": "i_am_author_of_label_and_note",
    }


def create(owner: TestClient, hid: str, *, url: str | None = None, key: str | None = None) -> dict:
    response = owner.post(
        path(hid), json=payload(url) if url else payload(), headers=headers(owner, key)
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def linked(
    owner: TestClient, hid: str, clients: ClientFactory, role: str
) -> tuple[TestClient, dict]:
    recipient = account(clients)
    invited = owner.post(
        f"/api/v1/households/{hid}/invite",
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


def counts(engine: Engine) -> tuple[int, int]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0
            for model in (RecipeLink, AuditEvent)
        )


def protected_snapshot(engine: Engine) -> dict:
    with Session(engine) as session:
        return {
            model.__tablename__: [
                tuple(
                    copy.deepcopy(getattr(row, column.name)) for column in model.__table__.columns
                )
                for row in session.scalars(select(model).order_by(model.id))
            ]
            for model in (Recipe, RecipeVersion, NutritionProfile)
        }


def assert_bookmark_only(link: dict) -> None:
    assert link["status"] == "link_only"
    assert link["version"] == 1
    assert link["planner_eligible"] is False
    assert link["automatic_fetch_enabled"] is False
    assert link["license"] is None
    assert link["nutrition_status"] == "unknown"
    assert link["allergen_status"] == "unknown"
    assert not {
        "kcal",
        "nutrients",
        "ingredients",
        "servings",
        "storage_method",
        "allergen_safe",
        "validation_status",
    }.intersection(link)


def test_literal_notes_preserve_existing_recipes_profiles_and_refs_only_metadata(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    seeded = owner.post(
        "/api/v1/households/demo",
        json={"confirmation": "create_separate_demo"},
        headers=headers(owner),
    )
    assert seeded.status_code == 201
    hid = seeded.json()["household"]["id"]
    before = protected_snapshot(migrated_engine)
    assert [len(rows) for rows in before.values()] == [3, 3, 2]
    key = str(uuid4())
    saved = create(owner, hid, key=key)
    assert_bookmark_only(saved)
    assert saved["own_note"] == payload()["own_note"]
    assert saved["source_url"].endswith("#skladniki")
    assert saved["canonical_url"] == "https://aniagotuje.pl/przepis/pomysl"
    assert saved["source_id"] == "aniagotuje"
    assert create(owner, hid, key=key) == saved
    assert protected_snapshot(migrated_engine) == before
    with Session(migrated_engine) as session:
        audit = session.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == UUID(saved["id"]))
        ).all()
        assert len(audit) == 1
        encoded_audit = json.dumps([event.__dict__ for event in audit], default=str)
        assert payload()["source_url"] not in encoded_audit
        assert payload()["own_note"] not in encoded_audit
        records = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.key == key)
        ).all()
        assert len(records) == 1
        assert len(records[0].result) == 1
        assert list(records[0].result.values()) == [saved["id"]]


def test_known_and_unknown_site_posts_perform_no_http_or_dns_work(
    clients: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = account(clients)
    hid = home(owner)
    incoming = headers(owner)
    calls = []

    def forbidden(*args: object, **kwargs: object) -> object:
        calls.append(True)
        raise AssertionError("Unexpected outbound HTTP or Python DNS operation")

    # Actual PostgreSQL libpq transport remains real; only HTTP/DNS APIs are spied.
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "gethostbyname", forbidden)
    monkeypatch.setattr(socket, "gethostbyname_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    for domain, source in [
        ("mealime.com", "mealime"),
        ("aniagotuje.pl", "aniagotuje"),
        ("www.kwestiasmaku.com", "kwestiasmaku"),
        ("unknown-recipes.example.com", None),
    ]:
        response = owner.post(
            path(hid),
            json=payload(f"https://{domain}/recipe"),
            headers={**incoming, "Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201
        assert response.json()["source_id"] == source
        assert_bookmark_only(response.json())
    for value in ["https://127.0.0.1/x", "https://2130706433/x", "https://localhost/x"]:
        assert (
            owner.post(
                path(hid),
                json=payload(value),
                headers={**incoming, "Idempotency-Key": str(uuid4())},
            ).status_code
            == 422
        )
    assert calls == []


@pytest.mark.parametrize(
    "url",
    [
        "http://aniagotuje.pl/x",
        "https://user:secret@aniagotuje.pl/x",
        "https://aniagotuje.pl:444/x",
        "https://localhost/x",
        "https://food.local/x",
        "https://food.internal/x",
        "https://food.invalid/x",
        "https://food.test/x",
        "https://127.1/x",
        "https://2130706433/x",
        "https://0x7f000001/x",
        "https://0177.0.0.1/x",
        "https://[::1]/x",
        "https://169.254.169.254/latest",
        "https://aniagotuje.pl\\@127.0.0.1/x",
        "https://aniagotuje.pl/%zz",
        "https://aniagotuje.pl/\nx",
        "https://aniagotuje.pl../x",
    ],
)
def test_unsafe_or_numeric_url_shape_is_rejected_without_mutation(
    clients: ClientFactory,
    migrated_engine: Engine,
    url: str,
) -> None:
    owner = account(clients)
    hid = home(owner)
    before = counts(migrated_engine)
    response = owner.post(path(hid), json=payload(url), headers=headers(owner))
    assert response.status_code == 422
    assert counts(migrated_engine) == before


def test_client_cannot_upgrade_registry_or_literal_notes_to_fetch_rights_or_structured_claims(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    before = counts(migrated_engine)
    for field, value in {
        "automatic_fetch_enabled": True,
        "license": "CC0-1.0",
        "source_id": "permissioned_api",
        "nutrition_status": "verified",
        "allergen_status": "safe",
        "planner_eligible": True,
        "ingredients": [],
        "kcal": 0,
        "storage_method": "shelf_stable",
        "status": "validated",
    }.items():
        submitted = payload()
        submitted[field] = value
        assert owner.post(path(hid), json=submitted, headers=headers(owner)).status_code == 422
    assert counts(migrated_engine) == before
    assert_bookmark_only(create(owner, hid))


def test_url_identity_preserves_path_query_order_and_opening_fragment_with_tenant_dedup(
    clients: ClientFactory,
) -> None:
    owner, other = account(clients), account(clients)
    hid, other_hid = home(owner), home(other)
    opening = "HTTPS://ANIAGOTUJE.PL.:443/przepis//a%2Fb?b=2&a=1#moja-sekcja"
    saved = create(owner, hid, url=opening)
    assert saved["source_url"] == "https://aniagotuje.pl/przepis//a%2Fb?b=2&a=1#moja-sekcja"
    assert saved["canonical_url"] == "https://aniagotuje.pl/przepis//a%2Fb?b=2&a=1"
    duplicate = owner.post(
        path(hid), json=payload(saved["canonical_url"] + "#inny-fragment"), headers=headers(owner)
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "RECIPE_LINK_EXISTS"
    assert create(other, other_hid, url=saved["source_url"])["id"] != saved["id"]
    distinct = create(owner, hid, url="https://aniagotuje.pl/przepis//a%2Fb?a=1&b=2")
    assert distinct["id"] != saved["id"]


def test_household_idor_viewer_downgrade_and_revocation_reauthorize_original_replay(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner, outsider = account(clients), account(clients)
    hid, other_hid = home(owner), home(outsider)
    editor, membership = linked(owner, hid, clients, "editor")
    key = str(uuid4())
    saved = create(editor, hid, key=key)
    assert outsider.get(path(hid)).status_code == 404
    assert outsider.get(path(hid, saved["id"])).status_code == 404
    assert outsider.get(path(other_hid, saved["id"])).status_code == 404
    assert outsider.post(path(hid), json=payload(), headers=headers(outsider)).status_code == 404
    access_path = f"/api/v1/households/{hid}/members/{membership['id']}/access"
    downgraded = owner.put(
        access_path,
        json={
            "expected_version": membership["access_version"],
            "role": "viewer",
            "access_enabled": True,
        },
        headers=headers(owner),
    )
    assert downgraded.status_code == 200
    assert editor.get(path(hid, saved["id"])).status_code == 200
    before = counts(migrated_engine)
    assert editor.post(path(hid), json=payload(), headers=headers(editor, key)).status_code == 403
    assert (
        editor.post(
            path(hid), json=payload("https://aniagotuje.pl/nowy"), headers=headers(editor)
        ).status_code
        == 403
    )
    assert counts(migrated_engine) == before
    assert (
        owner.put(
            access_path,
            json={
                "expected_version": downgraded.json()["access_version"],
                "role": "viewer",
                "access_enabled": False,
            },
            headers=headers(owner),
        ).status_code
        == 200
    )
    before = counts(migrated_engine)
    for url in [path(hid), path(hid, saved["id"])]:
        assert editor.get(url).status_code == 404
    assert editor.post(path(hid), json=payload(), headers=headers(editor, key)).status_code == 404
    assert counts(migrated_engine) == before
    assert owner.get(path(hid, saved["id"])).json() == saved


def test_unauth_origin_csrf_key_conflicts_cannot_change_saved_link(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    assert clients().get(path(hid)).status_code == 401
    before = counts(migrated_engine)
    for field, value in [("Origin", "https://evil.example"), ("X-CSRF-Token", "bad")]:
        incoming = headers(owner)
        incoming[field] = value
        assert owner.post(path(hid), json=payload(), headers=incoming).status_code == 403
    assert counts(migrated_engine) == before
    key = str(uuid4())
    saved = create(owner, hid, key=key)
    changed = payload()
    changed["own_note"] = "Inna notatka pod starym kluczem"
    assert owner.post(path(hid), json=changed, headers=headers(owner, key)).status_code == 409
    assert owner.get(path(hid, saved["id"])).json() == saved


def test_two_independent_editor_sessions_racing_one_url_commit_once(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    editor, _ = linked(owner, hid, clients, "editor")
    actors = [owner, editor]
    incoming = [headers(actor) for actor in actors]
    gate = Barrier(2)
    before = counts(migrated_engine)

    def save(index: int) -> int:
        gate.wait(timeout=10)
        return actors[index].post(path(hid), json=payload(), headers=incoming[index]).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(save, [0, 1]))
    assert sorted(statuses) == [201, 409]
    assert counts(migrated_engine) == (before[0] + 1, before[1] + 1)


def test_link_rows_are_immutable_and_pagination_reaches_distinct_summaries(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    saved = [create(owner, hid, url=f"https://aniagotuje.pl/strona/{index}") for index in range(3)]
    first = owner.get(path(hid), params={"limit": 2}).json()
    second = owner.get(path(hid), params={"limit": 2, "after": first["next_cursor"]}).json()
    assert len(first["recipe_links"]) == 2 and len(second["recipe_links"]) == 1
    assert second["next_cursor"] is None
    assert {link["id"] for link in first["recipe_links"] + second["recipe_links"]} == {
        link["id"] for link in saved
    }
    assert all("own_note" not in link for link in first["recipe_links"])
    assert owner.get(path(hid), params={"limit": 21}).status_code == 422
    assert owner.get(path(hid), params={"after": "bad"}).status_code == 422
    for statement in [
        "UPDATE recipe_links SET own_note='changed' WHERE id=:id",
        "DELETE FROM recipe_links WHERE id=:id",
    ]:
        with pytest.raises(IntegrityError) as blocked, migrated_engine.begin() as connection:
            connection.execute(text(statement), {"id": UUID(saved[0]["id"])})
        assert blocked.value.orig.sqlstate == "23514"
    assert owner.get(path(hid, saved[0]["id"])).json() == saved[0]


def test_url_note_and_actual_utf8_body_limits_do_not_partial_write(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    before = counts(migrated_engine)
    for field, value in [
        ("source_url", "https://aniagotuje.pl/" + "ą" * 1100),
        ("own_note", "x" * 2001),
        ("user_title", "x" * 161),
    ]:
        submitted = payload()
        submitted[field] = value
        assert owner.post(path(hid), json=submitted, headers=headers(owner)).status_code == 422
    raw = json.dumps({**payload(), "own_note": "🥕" * 4500}, ensure_ascii=False).encode()
    assert len(raw) > 16384
    assert (
        owner.post(
            path(hid), content=raw, headers={**headers(owner), "Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert counts(migrated_engine) == before


def test_permissive_future_registry_only_classifies_and_never_grants_network_or_content_rights(
    clients: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mealforge.recipes.links import routes

    owner = account(clients)
    hid = home(owner)
    incoming = headers(owner)
    permissive = {
        "checked_at": "2026-10-10",
        "default_mode": "permissioned_api",
        "default_automatic_fetch": True,
        "sources": [
            {
                "id": "permissive_future_source",
                "domains": ["permission.example.com"],
                "access_mode": "permissioned_api",
                "automatic_fetch_enabled": True,
                "license": "CC0-1.0",
            }
        ],
    }
    monkeypatch.setattr(routes, "load_source_registry", lambda: permissive)
    called = []

    def forbidden(*args: object, **kwargs: object) -> object:
        called.append(True)
        raise AssertionError("Registry classification triggered outbound work")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    response = owner.post(
        path(hid), json=payload("https://permission.example.com/my-recipe"), headers=incoming
    )
    assert response.status_code == 201
    assert response.json()["source_id"] == "permissive_future_source"
    assert_bookmark_only(response.json())
    assert called == []


def test_same_actor_distinct_sessions_concurrent_key_returns_one_persisted_link(
    clients: ClientFactory,
    migrated_engine: Engine,
) -> None:
    owner = account(clients)
    hid = home(owner)
    email = owner.get("/api/v1/auth/session").json()["user"]["email"]
    second_session = clients()
    assert (
        second_session.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            headers={"Origin": ORIGIN},
        ).status_code
        == 200
    )
    actors = [owner, second_session]
    key = str(uuid4())
    incoming = [headers(actor, key) for actor in actors]
    gate = Barrier(2)
    before = counts(migrated_engine)

    def save(index: int) -> dict:
        gate.wait(timeout=10)
        response = actors[index].post(path(hid), json=payload(), headers=incoming[index])
        assert response.status_code == 201
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save, [0, 1]))
    assert responses[0] == responses[1]
    assert counts(migrated_engine) == (before[0] + 1, before[1] + 1)
