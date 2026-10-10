import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as DatabaseTimeoutError
from sqlalchemy.orm import Session

from mealforge.core.config import Settings
from mealforge.core.database import session_factory
from mealforge.core.problems import Problem
from mealforge.households.models import AuditEvent, IdempotencyRecord

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {
        "description": "Żądanie odrzucone lub usługa niedostępna.",
        "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
    }
    for status in (401, 403, 404, 409, 413, 415, 422, 429, 503)
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message


def now() -> datetime:
    return datetime.now(UTC)


def get_settings(request: Request) -> Settings:
    settings = request.app.state.settings
    assert isinstance(settings, Settings)
    return settings


def get_session(request: Request) -> Iterator[Session]:
    engine = request.app.state.engine
    if engine is None:
        raise ApiError(503, "SERVICE_NOT_READY", "Usługa nie jest jeszcze gotowa.")
    try:
        with session_factory(engine).begin() as session:
            yield session
    except (OperationalError, DatabaseTimeoutError):
        raise ApiError(503, "SERVICE_NOT_READY", "Usługa nie jest jeszcze gotowa.") from None


Db = Annotated[Session, Depends(get_session, scope="function")]
Configuration = Annotated[Settings, Depends(get_settings)]


def audit(
    session: Session,
    request: Request,
    actor: UUID,
    household: UUID,
    action: str,
    entity_type: str,
    entity: UUID,
    before: int | None = None,
    after: int | None = None,
) -> None:
    session.add(
        AuditEvent(
            household_id=household,
            actor_user_id=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity,
            version_before=before,
            version_after=after,
            request_id=request.state.request_id,
            created_at=now(),
        )
    )


def mutate(
    session: Session,
    request: Request,
    actor: UUID,
    scope: str,
    command: str,
    payload: dict[str, Any],
    operation: Callable[[], dict[str, Any]],
    replay_authorize: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    incoming = request.headers.get("Idempotency-Key", "")
    try:
        key = str(UUID(incoming))
    except ValueError:
        raise ApiError(
            422, "IDEMPOTENCY_KEY_REQUIRED", "Wymagany poprawny identyfikator operacji."
        ) from None
    fingerprint = sha256(
        json.dumps(
            {"command": command, "payload": payload}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    lock_key = int.from_bytes(sha256(f"{actor}:{scope}:{key}".encode()).digest()[:8], signed=True)
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    previous = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.actor_user_id == actor,
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key == key,
        )
    )
    if previous:
        if replay_authorize:
            replay_authorize(previous.result)
        if previous.fingerprint != fingerprint:
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Identyfikator operacji został już użyty dla innych danych.",
            )
        return previous.result
    result = operation()
    session.add(
        IdempotencyRecord(
            actor_user_id=actor,
            scope=scope,
            key=key,
            fingerprint=fingerprint,
            result=result,
            created_at=now(),
        )
    )
    session.flush()
    return result
