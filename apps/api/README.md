# MealForge API — WAVE-00 baseline

Python 3.12, FastAPI/Pydantic 2, SQLAlchemy, psycopg, Alembic. From repository root:

```bash
uv sync --project apps/api --frozen
uv run --project apps/api --env-file .env alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api --env-file .env python -m mealforge.seed
uv run --project apps/api --env-file .env uvicorn mealforge.main:app --host 127.0.0.1 --port 8000 --no-access-log
uv run --project apps/api --env-file .env pytest apps/api/tests
uv run --project apps/api ruff check apps/api
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
uv run --project apps/api python -m mealforge.openapi --output contracts/openapi.yaml --check
```

`DATABASE_URL` uses `postgresql+psycopg://...`. `/health` is liveness, `/ready`
requires an active connection and exactly the current Alembic head. Readiness
queries have a three-second connection, statement, lock, and pool wait budget.
Errors are Polish `application/problem+json` with bounded UUID request IDs;
database addresses, credentials, and exception details are never responses.
Interactive API documentation is disabled; OpenAPI is generated offline from code.

Integration tests create and drop randomly named disposable PostgreSQL databases.
`TEST_DATABASE_URL` overrides the development `DATABASE_URL`; the test user needs
`CREATEDB`. Without either variable these integration tests are explicitly skipped.
The reference seed contains only five global Polish meal names; there are no
private households or invented nutrition values. Household and authentication
features belong to WAVE-01, and are not implemented by this baseline.
