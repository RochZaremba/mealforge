import json
from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from test_onboarding import headers, household, login, target

from mealforge.application import create_app
from mealforge.core.api import now
from mealforge.core.config import Settings
from mealforge.core.database import session_factory
from mealforge.households.models import (
    AuditEvent,
    HouseholdInvitation,
    HouseholdMember,
    IdempotencyRecord,
    NutritionProfile,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(postgres_settings: Settings) -> Settings:
    return Settings(
        database_url=postgres_settings.database_url,
        session_secret=SecretStr("test-secret-for-mealforge-over-thirty-two-characters"),
        app_env="test",
    )


def invite(
    owner: TestClient,
    csrf: str,
    hid: str,
    mid: str | None = None,
    role: str = "viewer",
    key: str | None = None,
) -> dict[str, object]:
    response = owner.post(
        f"/api/v1/households/{hid}/invite",
        json={"member_id": mid, "role": role},
        headers=headers(csrf, key),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_link_and_revoke_preserve_exact_nutrition_history(
    settings: Settings, migrated_engine: Engine
) -> None:
    app = create_app(settings)
    with TestClient(app) as owner, TestClient(app) as recipient:
        csrf = login(owner)
        hid = household(owner, csrf)
        member = owner.post(
            f"/api/v1/households/{hid}/members",
            json={"display_name": "Osobny profil"},
            headers=headers(csrf),
        ).json()
        mid = member["id"]
        path = f"/api/v1/households/{hid}/members/{mid}/nutrition-target"
        for version in range(2):
            assert (
                owner.put(
                    path,
                    json=target(
                        version, kcal_target="2700.001", protein_target_g="0", fat_target_g="1.234"
                    ),
                    headers=headers(csrf),
                ).status_code
                == 200
            )
        history = owner.get(path + "/history").json()
        invitation = invite(owner, csrf, hid, mid, "editor")
        recipient_csrf = login(recipient, "second@example.test")
        key = str(uuid4())
        accepted = recipient.post(
            "/api/v1/household-invitations/accept",
            json={"token": invitation["token"]},
            headers=headers(recipient_csrf, key),
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["member"]["id"] == mid
        assert accepted.json()["member"]["display_name"] == "Osobny profil"
        assert accepted.json()["member"]["version"] == 2
        assert accepted.json()["member"]["access_version"] == 1
        assert recipient.get(path + "/history").json() == history
        assert (
            recipient.post(
                "/api/v1/household-invitations/accept",
                json={"token": invitation["token"]},
                headers=headers(recipient_csrf),
            ).status_code
            == 409
        )
        assert (
            recipient.post(
                "/api/v1/household-invitations/accept",
                json={"token": invitation["token"]},
                headers=headers(recipient_csrf, key),
            ).json()
            == accepted.json()
        )
        access_path = f"/api/v1/households/{hid}/members/{mid}/access"
        downgraded = owner.put(
            access_path,
            json={"expected_version": 1, "role": "viewer", "access_enabled": True},
            headers=headers(csrf),
        )
        assert downgraded.status_code == 200
        current = recipient.get(f"/api/v1/households/{hid}").json()
        assert current["capabilities"] == {"can_edit": False, "can_manage_access": False}
        assert (
            recipient.put(path, json=target(2), headers=headers(recipient_csrf)).status_code == 403
        )
        revoked = owner.put(
            access_path,
            json={"expected_version": 2, "role": "viewer", "access_enabled": False},
            headers=headers(csrf),
        )
        assert revoked.status_code == 200 and revoked.json()["access_version"] == 3
        assert recipient.get(f"/api/v1/households/{hid}").status_code == 404
        assert recipient.get("/api/v1/households").json() == {"households": []}
        assert (
            recipient.post(
                "/api/v1/household-invitations/accept",
                json={"token": invitation["token"]},
                headers=headers(recipient_csrf, key),
            ).status_code
            == 404
        )
        assert owner.get(path + "/history").json() == history
        with session_factory(migrated_engine)() as db:
            linked = db.get(HouseholdMember, UUID(mid))
            assert linked is not None and linked.active and not linked.access_enabled
            assert linked.user_id is not None and linked.target_revision == 2
            assert db.scalar(select(func.count()).select_from(NutritionProfile)) == 2


def test_invite_replay_is_owner_only_and_never_persists_raw_code(
    settings: Settings, migrated_engine: Engine
) -> None:
    with TestClient(create_app(settings)) as owner:
        csrf = login(owner)
        hid = household(owner, csrf)
        key = str(uuid4())
        first = invite(owner, csrf, hid, key=key)
        assert invite(owner, csrf, hid, key=key) == first
        assert first["status"] == "pending"
        assert "token" not in owner.get(f"/api/v1/households/{hid}/invitations").text
        with session_factory(migrated_engine)() as db:
            invitation = db.scalar(select(HouseholdInvitation))
            assert invitation is not None
            assert invitation.token_hash == sha256(str(first["token"]).encode()).hexdigest()
            assert invitation.expires_at - invitation.created_at == timedelta(hours=24)
            rows = db.scalars(select(IdempotencyRecord)).all()
            assert str(first["token"]) not in json.dumps([row.result for row in rows])
            assert invitation.private_nonce not in json.dumps([row.result for row in rows])
            events = db.scalars(select(AuditEvent)).all()
            assert all(str(first["token"]) not in event.action for event in events)


@pytest.mark.parametrize("kind", ["expired", "revoked", "rotation"])
def test_closed_invitation_does_not_link_any_account(
    kind: str, settings: Settings, migrated_engine: Engine
) -> None:
    app = create_app(settings)
    with TestClient(app) as owner, TestClient(app) as recipient:
        csrf = login(owner)
        hid = household(owner, csrf)
        invitation = invite(owner, csrf, hid)
        if kind == "expired":
            with session_factory(migrated_engine).begin() as db:
                record = db.get(HouseholdInvitation, UUID(str(invitation["id"])))
                assert record is not None
                record.expires_at = now() - timedelta(seconds=1)
        elif kind == "revoked":
            response = owner.post(
                f"/api/v1/households/{hid}/invitations/{invitation['id']}/revoke",
                json={"expected_version": 1},
                headers=headers(csrf),
            )
            assert response.status_code == 200
        else:
            app.state.settings = settings.model_copy(
                update={
                    "session_secret": SecretStr("rotated-random-secret-over-thirty-two-characters")
                }
            )
        recipient_csrf = login(recipient, "recipient@example.test")
        response = recipient.post(
            "/api/v1/household-invitations/accept",
            json={"token": invitation["token"]},
            headers=headers(recipient_csrf),
        )
        assert response.status_code == (409 if kind == "rotation" else 410), response.text
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(HouseholdMember)) == 1
            record = db.get(HouseholdInvitation, UUID(str(invitation["id"])))
            assert record is not None and record.accepted_at is None


def test_owner_access_and_guests_are_protected(settings: Settings, migrated_engine: Engine) -> None:
    with TestClient(create_app(settings)) as owner:
        csrf = login(owner)
        hid = household(owner, csrf)
        member = owner.get(f"/api/v1/households/{hid}/members").json()["members"][0]
        response = owner.put(
            f"/api/v1/households/{hid}/members/{member['id']}/access",
            json={"expected_version": 0, "role": "viewer", "access_enabled": False},
            headers=headers(csrf),
        )
        assert (
            response.status_code == 409
            and response.json()["error_code"] == "OWNER_ACCESS_PROTECTED"
        )
        guest = owner.post(
            f"/api/v1/households/{hid}/members",
            json={"display_name": "Gość", "is_guest": True},
            headers=headers(csrf),
        ).json()
        response = owner.post(
            f"/api/v1/households/{hid}/invite",
            json={"member_id": guest["id"], "role": "viewer"},
            headers=headers(csrf),
        )
        assert response.status_code == 422
        with session_factory(migrated_engine)() as db:
            assert db.scalar(select(func.count()).select_from(HouseholdInvitation)) == 0
