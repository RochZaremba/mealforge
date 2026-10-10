import os
from typing import Literal, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, SecretStr, model_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    database_url: SecretStr | None = None
    session_secret: SecretStr | None = None
    trusted_origins: tuple[str, ...] = ("http://localhost:3000",)
    app_env: Literal["development", "test", "production"] = "development"
    session_ttl_seconds: int = 604800

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if not 300 <= self.session_ttl_seconds <= 2592000:
            raise ValueError("Nieprawidłowy czas sesji.")
        for origin in self.trusted_origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.path
                or url.query
                or url.fragment
                or url.username
                or url.password
                or "*" in origin
            ):
                raise ValueError("Nieprawidłowy zaufany origin.")
        if self.app_env == "production":
            if not self.session_secret or len(self.session_secret.get_secret_value()) < 32:
                raise ValueError("Brak bezpiecznej konfiguracji sesji.")
            if any(
                marker in self.session_secret.get_secret_value().lower()
                for marker in (
                    "change_me",
                    "changeme",
                    "placeholder",
                    "test-secret",
                    "ci-only",
                    "default",
                )
            ):
                raise ValueError("Brak bezpiecznej konfiguracji sesji.")
            if not self.trusted_origins or any(
                not item.startswith("https://") for item in self.trusted_origins
            ):
                raise ValueError("Produkcja wymaga HTTPS.")
            if not self.database_url:
                raise ValueError("Brak bezpiecznej konfiguracji bazy.")
            password = make_url(self.database_url.get_secret_value()).password or ""
            if len(password) < 20 or any(
                value in password.lower()
                for value in ("change_me", "changeme", "password", "placeholder")
            ):
                raise ValueError("Brak bezpiecznej konfiguracji bazy.")
        return self

    @classmethod
    def from_environment(cls) -> "Settings":
        value = os.environ.get("DATABASE_URL")
        if value:
            try:
                url = make_url(value)
                if url.drivername != "postgresql+psycopg" or not url.database:
                    raise ValueError
            except (ValueError, TypeError, ArgumentError):
                raise RuntimeError("Nieprawidłowa konfiguracja bazy danych.") from None
        try:
            return cls(
                database_url=SecretStr(value) if value else None,
                session_secret=SecretStr(os.environ["SESSION_SECRET"])
                if os.environ.get("SESSION_SECRET")
                else None,
                trusted_origins=tuple(
                    part.strip()
                    for part in os.environ.get("TRUSTED_ORIGINS", "http://localhost:3000").split(
                        ","
                    )
                    if part.strip()
                ),
                app_env=cast(
                    Literal["development", "test", "production"],
                    os.environ.get("APP_ENV", "development"),
                ),
                session_ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", "604800")),
            )
        except ValueError:
            raise RuntimeError("Nieprawidłowa konfiguracja usługi.") from None
