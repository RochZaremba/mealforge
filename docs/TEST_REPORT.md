# Test report — 2026-10-10

| Wave | Command | Exit | Actual result |
|---|---|---|---|
| bootstrap | python3 scripts/validate_kit.py | 0 | 139 passed, 0 failed, 1 skipped (brak jsonschema) |
| W00 tooling | /tmp/mealforge-tools-venv/bin/python scripts/validate_kit.py | 0 | 144 passed, 0 failed, 0 skipped po instalacji jsonschema/PyYAML |
| W00 database | docker compose --env-file .env -f compose.dev.yml up -d --wait postgres | 0 | PostgreSQL 16 zdrowy, bind 127.0.0.1:55432 |

## Integrated WAVE-00 actual gates (2026-10-10)

| Command | Exit | Result |
|---|---|---|
| uv sync --directory apps/api --frozen | 0 | Python3.12.15 / locked deps |
| pnpm install --frozen-lockfile | 0 | pnpm10.28.2, lock unchanged; unrs-resolver lifecycle script deliberately not enabled |
| make migrate openapi check-contract | 0 | real dev migration; generated OpenAPI3.1 exact drift check |
| make test | 0 | 16 pytest tests, including4 disposable PostgreSQL integration, no skips; backup integrity1 test passed |
| make migration-test | 0 | disposable up/check/seed twice/down/up/check; schema equal |
| make lint typecheck | 0 | Ruff, eslint, mypy14files, tsc |
| make build | 0 | Next16.4.0 production build9routes |
| PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/sbin/chromium make e2e | 0 | 10tests passed22.4s; desktop1440×900 and mobile390×844, realAPI readiness, network outage/retry,manifestPNG,SW public-cache/offline |
| make seed backup-test | 0 | actual pg_dump→authenticated encryption→verify/decrypt→new disposableDB pg_restore; all5 reference rows match |
| docker compose config --quiet | 0 | valid config, loopback bindings |
| make dev (first attempt) | 2 | transient Corepack npm request failure |
| make dev (second attempt) / compose run migrate | 2 | real Docker-only uv cache permission error for nonroot user; fixed migration command to installed Alembic executable; naprawa potwierdzona kolejnym make dev |
| pnpm audit --prod --json (security reviewer) | 0 | 97 dependencies, known vulnerabilities0 |
| pip-audit (security reviewer, initial) | 1 | pytest8.4.2 dev-only vulnerability; resolved by backend38bd7f to9.1.1 |
| pip-audit (security reviewer, after fix) | 0 | no known vulnerabilities; local editable unpublished package excluded |
| make test after pytest security fix | 0 | all16tests rerun passed1.74s, integrity1pass |

| make dev (third attempt) | 0 | all3 services healthy; nonroot direct Alembic migration0; real HTTP health/ready/status/proxyready200 |
| PLAYWRIGHT_NO_SERVER=1 make e2e (Docker + official bundle) | 0 |10tests passed6.4s, official Chrome156.0.8078.4 / Playwright1.64.0 against actual standalone Docker web and API |

One upstream Starlette/TestClient httpx deprecation warning, without failed tests. Actual local browser: system Chromium153.0.8010.52 on Arch, Playwright1.64.0; official browser bundle also installed and tested against Docker; Actions for final Compose-fix head still pending. Screenshots under docs/evidence/wave-00. Independent reviewer approved local gate after their own Docker HTTP smoke. Full product domain A01–A15 remain future-wave acceptance, not completed by shell smoke.


Audit nutrition/integrations: istniejące syntetyczne fixtures nie zawierają fikcyjnych wartości nutrient; fetch wszystkich źródeł wyłączony. Przed W01 kontrakt makro wymaga null; przed W02 import contract musi wymusić link-only/draft/provenance.

## CI feedback loop
Actions38063054961 (f2bbfe6): all validation/test/build/E2E steps successful, overall failure at setup-uv post-cleanup. uv run hosting long-lived API held cache lock; uv cache prune waited300s then failed. Fix: direct installed uvicorn for CI service, direct Next CLI, EXIT trap kills/waits both servers, job budget15minutes. New head CI required before merge; no checks skipped.

Actions38066342121 (9ff35f1): direct API healthy, web failed HTTP readiness because Next CLI ran in monorepo root without app directory. Independently reproduced locally (exit1, missing root .next) and reviewer identified same. Fixed explicit start apps/web directory; local corrected startup on3002 and /status200 confirmed. Server logs attached to CI artifacts for failures. Next exact-head CI still required.

W00 final gate: Actions38066767207 and38066764096 SUCCESS on exact head185425a108c614b4022c07a6860b956900058b88, including post-job cleanup. PR #1 merged62fe10c. W01-A tests not run yet.
