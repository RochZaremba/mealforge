import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from threading import BoundedSemaphore
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from mealforge.core.api import PROBLEM_RESPONSES, ApiError, Configuration, Db, now
from mealforge.core.config import Settings
from mealforge.identity.models import AuthRateBucket, ServerSession, User

router = APIRouter(prefix="/api/v1/auth", tags=["identity"], responses=PROBLEM_RESPONSES)
hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
hash_work = BoundedSemaphore(2)
dummy_hash = hasher.hash("This-is-a-dummy-password-not-an-account")
COOKIE_NAME = "mealforge_session"


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+", value):
            raise ValueError("Nieprawidłowy adres e-mail.")
        return value


class RegisterInput(LoginInput):
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Nieprawidłowa nazwa.")
        return value


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str


class RegisterResponse(BaseModel):
    user: UserResponse


class SessionResponse(RegisterResponse):
    csrf_token: str
    expires_at: str


@dataclass
class Authenticated:
    user: User
    server_session: ServerSession


def secret(settings: Settings) -> bytes:
    if not settings.session_secret or len(settings.session_secret.get_secret_value()) < 32:
        raise ApiError(503, "AUTH_NOT_CONFIGURED", "Logowanie nie jest jeszcze skonfigurowane.")
    return settings.session_secret.get_secret_value().encode()


def require_origin(request: Request, settings: Settings) -> None:
    secret(settings)
    if request.headers.get("Origin") not in settings.trusted_origins:
        raise ApiError(403, "ORIGIN_REJECTED", "Żądanie pochodzi z niedozwolonej strony.")
    if (
        request.method != "GET"
        and request.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json"
    ):
        raise ApiError(415, "JSON_REQUIRED", "Wymagane dane w formacie JSON.")


def csrf_token(settings: Settings, token_hash: str) -> str:
    return hmac.new(secret(settings), f"csrf:{token_hash}".encode(), "sha256").hexdigest()


def current_auth(request: Request, db: Db, settings: Configuration) -> Authenticated:
    secret(settings)
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", cookie):
        raise ApiError(401, "AUTH_REQUIRED", "Zaloguj się, aby kontynuować.")
    record = db.scalar(
        select(ServerSession)
        .where(
            ServerSession.token_hash == sha256(cookie.encode()).hexdigest(),
            ServerSession.revoked_at.is_(None),
            ServerSession.expires_at > now(),
        )
        .with_for_update()
    )
    if record is None:
        raise ApiError(401, "AUTH_REQUIRED", "Zaloguj się, aby kontynuować.")
    user = db.get(User, record.user_id)
    if user is None:
        raise ApiError(401, "AUTH_REQUIRED", "Zaloguj się, aby kontynuować.")
    return Authenticated(user, record)


Auth = Annotated[Authenticated, Depends(current_auth, scope="function")]


def require_mutation(request: Request, settings: Settings, auth: Authenticated) -> None:
    require_origin(request, settings)
    incoming = request.headers.get("X-CSRF-Token", "")
    if not re.fullmatch(r"[0-9a-f]{64}", incoming) or not hmac.compare_digest(
        incoming, csrf_token(settings, auth.server_session.token_hash)
    ):
        raise ApiError(403, "CSRF_REJECTED", "Nie udało się potwierdzić bezpieczeństwa żądania.")


def user_response(user: User) -> dict[str, str]:
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name}


def throttle(request: Request, settings: Settings, email: str, command: str) -> None:
    engine = request.app.state.engine
    if engine is None:
        raise ApiError(503, "SERVICE_NOT_READY", "Usługa nie jest jeszcze gotowa.")
    instant = now()
    window = int(instant.timestamp()) // 300
    peer = request.client.host if request.client else "unknown"
    limits = [("global", 200), (f"{command}:ip:{peer}", 40), (f"{command}:email:{email}", 8)]
    allowed = True
    # Separate committed transaction: rejected login attempts must remain counted.
    with engine.begin() as connection:
        expired = (
            select(AuthRateBucket.bucket_key, AuthRateBucket.window)
            .where(AuthRateBucket.expires_at < instant)
            .limit(100)
        )
        connection.execute(
            delete(AuthRateBucket).where(
                tuple_(AuthRateBucket.bucket_key, AuthRateBucket.window).in_(expired)
            )
        )
        for name, limit in limits:
            key = hmac.new(secret(settings), f"rate:{name}".encode(), "sha256").hexdigest()
            statement = insert(AuthRateBucket).values(
                bucket_key=key,
                window=window,
                attempts=1,
                expires_at=instant + timedelta(minutes=10),
            )
            counted = statement.on_conflict_do_update(
                index_elements=[AuthRateBucket.bucket_key, AuthRateBucket.window],
                set_={"attempts": AuthRateBucket.attempts + 1},
                where=AuthRateBucket.attempts < limit,
            ).returning(AuthRateBucket.attempts)
            if connection.scalar(counted) is None:
                allowed = False
                break
    if not allowed:
        raise ApiError(429, "AUTH_RATE_LIMITED", "Za dużo prób. Spróbuj ponownie za kilka minut.")


@router.post("/register", status_code=201, response_model=RegisterResponse)
def register(
    payload: RegisterInput, request: Request, db: Db, settings: Configuration
) -> dict[str, object]:
    require_origin(request, settings)
    throttle(request, settings, payload.email, "register")
    if not hash_work.acquire(timeout=1):
        raise ApiError(429, "AUTH_RATE_LIMITED", "Za dużo prób. Spróbuj ponownie później.")
    try:
        password_hash = hasher.hash(payload.password)
    finally:
        hash_work.release()
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=password_hash,
        created_at=now(),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        raise ApiError(
            409, "REGISTRATION_CONFLICT", "Nie można utworzyć konta dla podanych danych."
        ) from None
    return {"user": user_response(user)}


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginInput, request: Request, response: Response, db: Db, settings: Configuration
) -> dict[str, object]:
    require_origin(request, settings)
    throttle(request, settings, payload.email, "login")
    user = db.scalar(select(User).where(User.email == payload.email))
    if not hash_work.acquire(timeout=1):
        raise ApiError(429, "AUTH_RATE_LIMITED", "Za dużo prób. Spróbuj ponownie później.")
    try:
        valid: bool
        try:
            valid = hasher.verify(user.password_hash if user else dummy_hash, payload.password)
        except (VerificationError, InvalidHashError):
            valid = False
        if valid and user and hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hasher.hash(payload.password)
    finally:
        hash_work.release()
    if not user or not valid:
        raise ApiError(401, "INVALID_CREDENTIALS", "Nieprawidłowy adres e-mail lub hasło.")
    previous = request.cookies.get(COOKIE_NAME, "")
    if previous:
        old = db.scalar(
            select(ServerSession)
            .where(ServerSession.token_hash == sha256(previous.encode()).hexdigest())
            .with_for_update()
        )
        if old:
            old.revoked_at = now()
    token = secrets.token_urlsafe(32)
    instant = now()
    expired = select(ServerSession.token_hash).where(ServerSession.expires_at < instant).limit(100)
    db.execute(delete(ServerSession).where(ServerSession.token_hash.in_(expired)))
    record = ServerSession(
        token_hash=sha256(token.encode()).hexdigest(),
        user_id=user.id,
        created_at=instant,
        expires_at=instant + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(record)
    db.flush()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )
    return {
        "user": user_response(user),
        "csrf_token": csrf_token(settings, record.token_hash),
        "expires_at": record.expires_at.isoformat(),
    }


@router.get("/session", response_model=SessionResponse)
def session_info(auth: Auth, settings: Configuration) -> dict[str, object]:
    return {
        "user": user_response(auth.user),
        "csrf_token": csrf_token(settings, auth.server_session.token_hash),
        "expires_at": auth.server_session.expires_at.isoformat(),
    }


@router.post("/logout", status_code=204)
def logout(
    request: Request, response: Response, db: Db, settings: Configuration, auth: Auth
) -> None:
    require_mutation(request, settings, auth)
    auth.server_session.revoked_at = now()
    response.delete_cookie(
        COOKIE_NAME,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )
