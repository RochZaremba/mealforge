"""Generate deterministic OpenAPI without a database or network dependency."""

import argparse
import json
from pathlib import Path

from mealforge.application import create_app
from mealforge.core.config import Settings


def generate_openapi() -> str:
    return (
        json.dumps(create_app(Settings()).openapi(), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    content = generate_openapi()
    if arguments.check:
        if not arguments.output.exists() or arguments.output.read_text(encoding="utf-8") != content:
            raise SystemExit("Kontrakt OpenAPI różni się od implementacji API.")
    else:
        arguments.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
