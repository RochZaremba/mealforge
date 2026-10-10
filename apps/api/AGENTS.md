# API-specific agent rules

- Follow root AGENTS.md and docs/API_CONTRACTS.md. Use FastAPI, SQLAlchemy, Pydantic v2, Alembic, typed layers; use database transactions for domain state.
- Always scope queries by household and authenticated memberships; IDs alone are not authorization.
- API validation: external ingredient nutrient data may be unknown; do not replace null with zero.
- Mutating routes require idempotency keys for cooking, purchases, consumption and plan commit.
- Never fetch user-provided URL without SSRF-safe allow/deny controls and rights gate.
- Add integration tests for each persistence boundary and migration.
