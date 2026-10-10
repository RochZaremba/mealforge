from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"


class Problem(BaseModel):
    error_code: str
    message: str
    request_id: str
    field_errors: dict[str, str] | None = None
