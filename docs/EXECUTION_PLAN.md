# Execution plan — 2026-10-10

## WAVE-00: runnable baseline (local gates PASS; final PR CI pending)
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
