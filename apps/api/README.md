# MealForge API — private household and original recipe slices

Python 3.12, FastAPI/Pydantic 2, SQLAlchemy, psycopg, Alembic. From repository root:

```bash
uv sync --project apps/api --frozen
uv run --project apps/api --env-file .env alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api --env-file .env python -m mealforge.seed
uv run --project apps/api --env-file .env uvicorn mealforge.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
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
The reference seed contains only five global Polish meal names; it never creates
accounts, private households, diet targets or invented nutrition values.

W01-A adds `/api/v1/auth` register/login/session/logout and authorized household,
member, target-history and meal-slot configuration endpoints. Registration requires
an explicit login. Set `SESSION_SECRET` (at least 32 characters), `APP_ENV` and
comma-separated `TRUSTED_ORIGINS` (development default `http://localhost:3000`).
Production requires HTTPS origins, strong non-placeholder session and database
credentials, and secure cookies. `SESSION_TTL_SECONDS` defaults to seven days.
Never enable proxy headers from arbitrary clients: auth rate limits use the direct
peer, which is shared when Next.js proxies requests; email buckets apply separately.

Unsafe requests require trusted `Origin` and JSON; private mutations additionally
require `X-CSRF-Token` from session GET and UUID `Idempotency-Key` (logout only needs
CSRF). Actual request bytes are capped at 16 KiB with a five-second upload timeout.
Password length is 12–128 characters; Argon2id work is bounded to two concurrent
hashes. Rate buckets are HMAC identifiers in PostgreSQL, counting failed attempts.

Targets accept canonical decimal strings or integers, rejecting float/bool input.
All four values must be supplied explicitly; unknown is `null`, genuine zero macro
is retained. Profiles append immutable history with optimistic versions, and warn
only when fully known `4P + 4C + 9F` differs from kcal by more than 5%. Targets have
current/past effective dates in this slice; future scheduling is rejected explicitly.
Slots are an atomic set of 1–12 rows, initially five; breakfast/dinner repetition is
a persisted preference, applied by the future planner. Nutrition calculations,
weekly plans and offline private data remain later slices.

W01-B adds owner-only 24-hour invitations and access administration. Codes are
64-character hex tokens returned only in create responses, submitted in JSON to
authenticated accept; they are never emailed, embedded in URLs, logged, or stored
in audit/idempotency JSON. A private random nonce and domain-separated HMAC derive
the token, with only its SHA256 hash used for lookup. Changing the session secret
invalidates pending codes and create replays explicitly. Household locks serialize
authorization, access changes, acceptance and revocation before invitation/member
locks; accepted codes cannot be consumed twice. Acceptance preserves an existing
non-guest resident profile and all immutable targets. Access revocation preserves
resident participation (`active`) while disabling account access (`access_enabled`).
Owners cannot revoke or demote themselves; owner identity is verified through
`owner_user_id`. Role/access changes have their own `access_version`, separate from
target history. Household DTOs expose current `can_edit`/`can_manage_access`
capabilities; private reads, writes, lists and retries all recheck current access.

W01-C adds private original recipe create/read/edit and immutable version history.
Every recipe remains `draft_requires_review`, `planner_eligible=false`; nutrients,
allergens, measured cooked yield, timing, prices and storage are explicitly unknown.
Ingredient amounts are positive canonical strings or integers, or `null`, with
literal units and raw/cooked/unknown state; no conversion is inferred. Own text
requires `rights_attestation=i_am_author` for the user's contribution. Original
MealForge fixture attribution stays in immutable lineage when edited; new user
contributions have no inferred public license. No external recipe is fetched.

Recipe lists use `limit` (1–20) and `after` UUID cursors, returning summaries and
`next_cursor`. History uses `limit` (1–5) and `before_version`, returning full snapshots
and `next_before_version`. Mutations share household locks, optimistic versions,
CSRF and idempotency; immutable history and a deferred composite current-version
foreign key are enforced in PostgreSQL. Idempotency stores references, not recipe text.

Only explicit POST `/api/v1/households/demo` with
`{"confirmation":"create_separate_demo"}` creates a separate owned demo household,
two sample 2700/1600 targets with null macros, five slots and three original drafts.
It never modifies another household. `source=demo_seed` and demo warnings persist
on household/target DTOs. The audited original fixture ships as an installed package
resource; absence, excessive size or integrity drift aborts demo creation atomically.

W02-A adds private create-only source bookmarks at
`/api/v1/households/{id}/recipe-links`. A user's own label/note and contribution
attestation are stored with a validated HTTPS opening URL, preserving its fragment.
The canonical deduplication URL removes only the fragment; household duplicates
with a new operation key return `409 RECIPE_LINK_EXISTS`. Same-key replay rechecks
current edit access and returns the original record. Immutable rows and bounded
2048-byte URLs are enforced by PostgreSQL; lists use `limit` 1–20 and `after` UUID.

URL validation is pure and performs no DNS, redirects or network request. Registry
classification is frozen metadata, not source rights approval. Every record stays
`link_only`, license unknown, nutrition/allergens unknown, automatic fetch disabled
and excluded from planning. User notes do not become structured nutrition/safety
claims. The complete source registry ships in the installed package with bounded
integrity-checked loading; absence or drift aborts creation. There is no edit,
delete, remote preview, parser or automatic import in this slice.
