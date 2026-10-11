import json
import socket
import urllib.request
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from test_jsonld import document
from test_onboarding import target
from test_recipe_links_security import account, headers, home, linked
from test_recipe_links_security import clients as clients

pytestmark = pytest.mark.integration


def body(raw=None):
    return {
        "document": raw or document(recipeYield="3 kg 700 g", nutrition={"calories": "0 kcal"}),
        "rights_attestation": "i_am_author",
    }


def route(hid):
    return f"/api/v1/households/{hid}/recipe-imports/preview"


def private_fingerprints(engine):
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"SELECT row_to_json(t)::text FROM {table} AS t ORDER BY id")
            )
            .scalars()
            .all()
            for table in (
                "recipes",
                "recipe_versions",
                "nutrition_profiles",
                "recipe_links",
                "audit_events",
                "idempotency_records",
                "household_members",
                "households",
            )
        }


def test_preview_no_network_or_persistence_and_no_claim_promotion(
    clients, migrated_engine, monkeypatch
):
    owner = account(clients)
    hid = home(owner)
    member = owner.get(f"/api/v1/households/{hid}/members").json()["members"][0]
    assert (
        owner.put(
            f"/api/v1/households/{hid}/members/{member['id']}/nutrition-target",
            json=target(kcal_target="100.125", protein_target_g="0"),
            headers=headers(owner),
        ).status_code
        == 200
    )
    assert (
        owner.post(
            f"/api/v1/households/{hid}/recipes",
            headers=headers(owner),
            json={
                "title": "Własny zapis przed podglądem",
                "instructions": ["Połącz."],
                "ingredients": [
                    {
                        "name": "składnik",
                        "amount": None,
                        "unit": "unknown",
                        "weight_state": "unknown",
                    }
                ],
                "rights_attestation": "i_am_author",
            },
        ).status_code
        == 201
    )
    before = private_fingerprints(migrated_engine)

    def forbidden(*args, **kwargs):
        raise AssertionError("Preview attempted outbound request")

    original = socket.getaddrinfo

    def dns(host, *args, **kwargs):
        if host not in ("localhost", "127.0.0.1", "::1"):
            return forbidden()
        return original(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    original_send = httpx.Client.send

    def local_send(client, request, *args, **kwargs):
        if request.url.host != "testserver":
            return forbidden()
        return original_send(client, request, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", local_send)
    session_headers = headers(owner)
    for _ in range(2):
        result = owner.post(route(hid), json=body(), headers=session_headers)
        assert result.status_code == 200
        assert result.headers["cache-control"] == "no-store"
        data = result.json()
        assert data["persisted"] is False and data["planner_eligible"] is False
        assert data["license"] is None
        assert data["allergen_status"] == data["nutrition_status"] == "unknown"
        assert data["recipe_yield_raw"] == ["3 kg 700 g"]
        assert all(
            item["amount"] is None and item["unit"] == item["weight_state"] == "unknown"
            for item in data["ingredients"]
        )
    assert before == private_fingerprints(migrated_engine)


def test_preview_current_auth_roles_idor_origin_csrf_and_revocation(clients):
    owner = account(clients)
    hid = home(owner)
    outsider = account(clients)
    assert outsider.post(route(hid), json=body(), headers=headers(outsider)).status_code == 404
    viewer, member = linked(owner, hid, clients, "viewer")
    assert viewer.post(route(hid), json=body(), headers=headers(viewer)).status_code == 403
    assert (
        owner.post(route(hid), json=body(), headers={"Origin": "http://localhost:3000"}).status_code
        == 403
    )
    bad_origin = {**headers(owner), "Origin": "https://attacker.invalid"}
    assert owner.post(route(hid), json=body(), headers=bad_origin).status_code == 403
    changed = owner.put(
        f"/api/v1/households/{hid}/members/{member['id']}/access",
        json={
            "expected_version": member["access_version"],
            "role": "editor",
            "access_enabled": True,
        },
        headers=headers(owner),
    )
    assert changed.status_code == 200
    assert viewer.post(route(hid), json=body(), headers=headers(viewer)).status_code == 200
    remembered = headers(viewer)
    revoked = owner.put(
        f"/api/v1/households/{hid}/members/{member['id']}/access",
        json={
            "expected_version": changed.json()["access_version"],
            "role": "editor",
            "access_enabled": False,
        },
        headers=headers(owner),
    )
    assert revoked.status_code == 200
    assert viewer.post(route(hid), json=body(), headers=remembered).status_code == 404
    assert owner.post(route(uuid4()), json=body(), headers=headers(owner)).status_code == 404


def test_preview_rights_protected_fields_and_malformed_body_fail_before_any_write(
    clients, migrated_engine
):
    owner = account(clients)
    hid = home(owner)
    before = private_fingerprints(migrated_engine)
    for payload in [
        body('{"private-sentinel":NaN}'),
        {"document": document()},
        {**body(), "rights_attestation": "licensed"},
        {**body(), "license": "CC0"},
        {**body(), "planner_eligible": True},
        {**body(), "document": True},
    ]:
        rejected = owner.post(route(hid), json=payload, headers=headers(owner))
        assert rejected.status_code == 422
        assert "private-sentinel" not in rejected.text
    rejected = owner.post(
        route(hid),
        content=json.dumps(body("x" * 17000)),
        headers={**headers(owner), "Content-Type": "application/json"},
    )
    assert rejected.status_code == 413
    assert before == private_fingerprints(migrated_engine)
