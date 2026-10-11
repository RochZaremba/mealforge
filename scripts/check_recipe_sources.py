"""Check the packaged classification registry; never enable remote fetching."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def read_registry(raw: bytes) -> dict:
    if len(raw) > 65536:
        raise ValueError
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("default_mode") != "link_only":
        raise ValueError
    if value.get("default_automatic_fetch") is not False:
        raise ValueError
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError
    if any(row.get("automatic_fetch_enabled") is not False for row in sources):
        raise ValueError
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true")
    args = parser.parse_args()
    try:
        from mealforge.core.api import ApiError
        from mealforge.recipes.links.registry import load_source_registry

        expected = read_registry((ROOT / "config/recipe_sources.json").read_bytes())
        packaged = read_registry(files("mealforge.recipes.links").joinpath(
            "recipe_sources.json").read_bytes())
        if packaged != expected:
            raise ValueError
        try:
            if load_source_registry() != expected:
                raise ValueError
        except ApiError:
            raise ValueError from None
        if args.docker:
            program = (
                "import hashlib,json; "
                "from mealforge.recipes.links.registry import load_source_registry; "
                "value=load_source_registry(); "
                "print(hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,"
                "separators=(',',':')).encode()).hexdigest())"
            )
            result = subprocess.run(
                ["docker", "compose", "--env-file", ".env", "-f", "compose.dev.yml", "exec",
                 "-T", "api", "/app/.venv/bin/python", "-c", program],
                cwd=ROOT, capture_output=True, timeout=30, check=False,
            )
            if result.returncode or result.stdout.decode().strip() != canonical_digest(expected):
                raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError, OSError, ImportError,
            subprocess.TimeoutExpired):
        print("FAIL: rejestr źródeł jest niedostępny, zmieniony lub aktywuje fetch.")
        return 1
    print("PASS: rejestr zgodny z repo i audytowanym loaderem; fetch wyłączony" +
          (" również w Docker." if args.docker else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
