#!/usr/bin/env python3
"""Compare the committed contract with deterministic, executable FastAPI OpenAPI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update generated contract")
    parser.add_argument("--contract", type=Path, default=ROOT / "contracts/openapi.yaml")
    args = parser.parse_args()
    # The backend exporter owns canonical generation and its drift checks.
    # Do not maintain an independent serialization implementation here.
    command = [sys.executable, "-m", "mealforge.openapi", "--output", str(args.contract)]
    if not args.write:
        command.append("--check")
    # Make loading the backend explicit even before editable install.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "apps/api/src")
    return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
