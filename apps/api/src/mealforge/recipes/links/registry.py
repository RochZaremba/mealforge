import json
from datetime import date
from hashlib import sha256
from importlib.resources import files
from typing import Any

from mealforge.core.api import ApiError

EXPECTED_REGISTRY_SHA256 = "8d78ba7c3893a6e0ffcbae30d5dac28c6f54d2a938b8c80a93051263b792fedb"


def load_source_registry() -> dict[str, Any]:
    """Classification metadata only; this resource grants no rights or network permission."""
    try:
        with files("mealforge.recipes.links").joinpath("recipe_sources.json").open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        registry = json.loads(raw)
        canonical = json.dumps(registry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if sha256(canonical.encode()).hexdigest() != EXPECTED_REGISTRY_SHA256:
            raise ValueError
        if registry["schema_version"] != 1:
            raise ValueError
        date.fromisoformat(registry["checked_at"])
        return dict(registry)
    except (OSError, KeyError, TypeError, ValueError):
        raise ApiError(
            503, "SOURCE_REGISTRY_UNAVAILABLE", "Rejestr źródeł nie jest dostępny."
        ) from None
