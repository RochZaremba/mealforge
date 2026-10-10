from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from mealforge.core.config import Settings
from mealforge.main import create_app
from mealforge.openapi import generate_openapi


def test_health_does_not_need_database() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["x-request-id"])
    assert response.headers["cache-control"] == "no-store"


def test_missing_database_readiness_is_not_success() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["error_code"] == "SERVICE_NOT_READY"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_unavailable_database_does_not_expose_secret() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql+psycopg://private-user:never-log-this@127.0.0.1:1/private-database"
        )
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    for secret in ("never-log-this", "private-user", "private-database", "127.0.0.1", "psycopg"):
        assert secret not in response.text


@pytest.mark.parametrize("incoming", [str(uuid4()), "untrusted-id", "a" * 512])
def test_request_id_is_bounded_uuid(incoming: str) -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health", headers={"X-Request-ID": incoming})
    actual = response.headers["x-request-id"]
    UUID(actual)
    assert actual == incoming if len(incoming) == 36 else actual != incoming


def test_unknown_resource_is_polish_problem_without_reflecting_path() -> None:
    with TestClient(create_app(Settings())) as client:
        response = client.get("/private-user/allergies")
    assert response.status_code == 404
    assert response.json()["message"] == "Nie znaleziono zasobu."
    assert "private-user" not in response.text


def test_internal_errors_are_sanitized(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(Settings())

    @app.get("/test-failure")
    def failure() -> None:
        raise RuntimeError("secret-password")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-failure")
    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    assert "secret-password" not in response.text
    assert "secret-password" not in caplog.text
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_openapi_is_deterministic_and_excludes_unimplemented_domains() -> None:
    import json

    assert generate_openapi() == generate_openapi()
    specification = json.loads(generate_openapi())
    assert {"/health", "/ready"} <= set(specification["paths"])
    assert not any(
        "recipe" in path or "invite" in path or "plans" in path for path in specification["paths"]
    )
    assert (
        "application/problem+json"
        in specification["paths"]["/ready"]["get"]["responses"]["503"]["content"]
    )


@pytest.mark.parametrize(
    "bad_url", ["not-a-url", "sqlite:///test.db", "postgresql://user:secret@host/db"]
)
def test_configuration_errors_do_not_echo_credentials(
    monkeypatch: pytest.MonkeyPatch, bad_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", bad_url)
    with pytest.raises(RuntimeError, match="Nieprawidłowa konfiguracja bazy danych") as error:
        Settings.from_environment()
    assert "secret" not in str(error.value)
