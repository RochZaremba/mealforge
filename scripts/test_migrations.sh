#!/usr/bin/env bash
# DATABASE_URL supplies PostgreSQL credentials; its database is NEVER migrated.
# The connected role needs CREATE DATABASE. Only a newly created UUID DB is dropped.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
uv run --project apps/api python - "$repo_root" <<'PY'
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

root = Path(sys.argv[1])
value = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not value:
    raise SystemExit("DATABASE_URL is required; provide a PostgreSQL role with CREATE DATABASE")
source = make_url(value)
if source.get_backend_name() != "postgresql":
    raise SystemExit("PostgreSQL is required for migration verification")

# Only this generated identifier is interpolated as SQL. No input database is mutated.
database = "mealforge_migration_test_" + uuid.uuid4().hex
admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
test_url = source.set(database=database)
test_engine = create_engine(test_url)
environment = dict(os.environ, DATABASE_URL=test_url.render_as_string(hide_password=False))
created = False


def migrate(*arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(root / "apps/api/alembic.ini"), *arguments],
        cwd=root,
        env=environment,
        check=True,
    )


def schema() -> dict:
    catalog = inspect(test_engine)
    result = {}
    for table in sorted(catalog.get_table_names()):
        if table == "alembic_version":
            continue
        result[table] = {
            "columns": [
                (item["name"], str(item["type"]), item["nullable"], item["default"])
                for item in catalog.get_columns(table)
            ],
            "primary_key": catalog.get_pk_constraint(table),
            "foreign_keys": catalog.get_foreign_keys(table),
            "unique": catalog.get_unique_constraints(table),
            "checks": catalog.get_check_constraints(table),
            "indexes": catalog.get_indexes(table),
        }
    return result


try:
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    created = True
    migrate("upgrade", "head")
    migrate("check")
    first = schema()
    if not first:
        raise RuntimeError("Upgrade created no application tables")
    # The real fixture command must be idempotent and use the disposable DB only.
    for _ in range(2):
        subprocess.run(
            [sys.executable, "-m", "mealforge.seed"], cwd=root, env=environment, check=True
        )
    with test_engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM meal_slot_definitions")).scalar_one()
        if count != 5:
            raise RuntimeError(f"Expected five meal-slot definitions after repeat seed; got {count}")
    migrate("downgrade", "base")
    if schema():
        raise RuntimeError("Downgrade left application tables behind")
    migrate("upgrade", "head")
    migrate("check")
    if first != schema():
        raise RuntimeError("Schema changed after upgrade/downgrade/upgrade")
    print("PASS: disposable PostgreSQL migration up/check/seed/down/up/check/schema round trip")
except SQLAlchemyError:
    # Avoid echoing connection URLs or credentials on connection errors.
    raise SystemExit("PostgreSQL migration test failed; check connectivity and CREATE DATABASE privilege") from None
finally:
    test_engine.dispose()
    if created:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                     "WHERE datname = :database AND pid <> pg_backend_pid()"),
                {"database": database},
            )
            connection.execute(text(f'DROP DATABASE "{database}"'))
    admin.dispose()
PY
