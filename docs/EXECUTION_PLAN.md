# Execution plan — 2026-10-10

## WAVE-00: runnable baseline (COMPLETE; PR #1 merged)
Cel: rzeczywiste FastAPI + PostgreSQL + Next.js, uruchamialne lokalnie i przez Docker Compose. Zakres nie obejmuje jeszcze prywatnych danych ani planowania.

| Owner | Branch / worktree | Exclusive files |
|---|---|---|
| lead | feat/wave-00-baseline, główny checkout | root workspace, compose, Makefile, scripts infra, CI, contracts, docs |
| backend | backend/wave-00, ../mealforge-worktrees/backend | apps/api/** |
| frontend | frontend/wave-00, ../mealforge-worktrees/frontend | apps/web/** poza QA paths |
| QA | qa/wave-00, ../mealforge-worktrees/qa | apps/web/e2e/**, apps/web/playwright.config.ts, scripts/check_openapi.py, scripts/test_migrations.sh |
| nutrition/integrations/security | read-only | niezależne review danych, licencji, bezpieczeństwa |

Remote podany przez użytkownika: https://github.com/RochZaremba/mealforge.git (puste publiczne repo). Początkowy SPEC KIT main jest publikowany jako baza, W00 trafi przez PR po testach/review. Sekrety i prywatne dane nie trafiają do Git.

Kontrakt W00: GET /health → {status: ok}; GET /ready → {status: ready} dopiero po DB i sprawdzeniu migracji. Niedostępność → 503 problem+json bez sekretów. Brak publicznych prywatnych endpointów. OpenAPI wygenerowane z API; przyszłe endpointy pozostają wymaganiami w API_CONTRACTS.

Kryteria: make dev uruchamia pełny Compose, realne API + DB smoke, migracja up/down/up disposable DB, frontend lint/typecheck/build, Playwright 390×844 i 1440×900, faktyczny stan dependency outage, manifest/ikony, brak prywatnego cache. make backup wykonuje szyfrowany pg_dump. CI wykonuje rzeczywiste komendy. Review niezależne, poprawki, ponowne testy, merge przez lead.

Testy: validate_kit, pytest (PostgreSQL), Ruff, mypy, OpenAPI drift, Alembic round-trip, eslint, tsc, Next production build, Playwright mobile/desktop, Compose startup/readiness, backup/restore disposable DB.

## Następna fala
WAVE-01 dopiero po zielonym gate W00: sessions/auth/household/profile history/5 editable slots/original recipes. Przed implementacją nowy plan i ADR sesji. B/W/T demo pozostają null dopóki użytkownik nie poda wartości; kalorie 2700/1600 tylko jawny demo seed.

## WAVE-01-A: sessions and household onboarding
Goal: authenticated private household with two independently editable member targets and real persisted daily meal-slot settings. Dependencies: W00 merged62fe10c, exact-head185425a CI and independent reviews PASS. No production deployment.

Ownership (separate worktrees/branches based on62fe10c): backend apps/api/** except QA security test; frontend apps/web/** except e2e/config; QA apps/web/e2e/households.spec.ts + apps/api/tests/test_household_security.py; nutrition fixtures/original-recipes.json and review; integrations/security read-only audit; lead contracts/docs/infra/OpenAPI/integration. No overlapping edits.

API /api/v1: auth register/login/session/logout; household list/create/read; member list/create; nutrition-target PUT expected_version and GET history; meal-slot-presets GET/PUT expected_version. Numeric target values Decimal strings or integers, unknown null, zero macro valid. No automatic calorie goals. Auth sessions hashed at rest, Argon2id, trusted-origin+session CSRF, DB-backed bounded auth throttling. All private endpoints authorize household membership, viewers read-only. Mutations use atomic audit and idempotency records and version conflict409. Production settings fail closed.

Tests: actual PostgreSQL migration roundtrip; login/logout/bad-password/throttle/CSRF/IDOR/role/version races/idempotency; exact Decimal targets and unknown macro; mobile390 and desktop1440 register→household→second member→edit goals→history→edit repeat/slots→reload; outage errors; lint/typecheck/build/OpenAPI drift and W00 regressions. Independent security/nutrition/reviewer before merge.

W01-A completion is a testable slice, not whole W01. W01-B single-use invitation/accept and W01-C private original recipes follow only after A passes. Demo2700/1600 explicit opt-in only. No recipe-network fetch or planner in this slice.
