import os

from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    database_url: SecretStr | None = None

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
        return cls(database_url=SecretStr(value) if value else None)
