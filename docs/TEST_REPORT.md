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

One upstream Starlette/TestClient httpx deprecation warning, without failed tests. Actual local browser: system Chromium153.0.8010.52 on Arch, Playwright1.64.0; official browser bundle also installed and tested against Docker; Final CI subsequently passed (record below). Screenshots under docs/evidence/wave-00. Independent reviewer approved local gate after their own Docker HTTP smoke. Full product domain A01–A15 remain future-wave acceptance, not completed by shell smoke.


Audit nutrition/integrations: istniejące syntetyczne fixtures nie zawierają fikcyjnych wartości nutrient; fetch wszystkich źródeł wyłączony. Przed W01 kontrakt makro wymaga null; przed W02 import contract musi wymusić link-only/draft/provenance.

## CI feedback loop
Actions38063054961 (f2bbfe6): all validation/test/build/E2E steps successful, overall failure at setup-uv post-cleanup. uv run hosting long-lived API held cache lock; uv cache prune waited300s then failed. Fix: direct installed uvicorn for CI service, direct Next CLI, EXIT trap kills/waits both servers, job budget15minutes. New head CI required before merge; no checks skipped.

Actions38066342121 (9ff35f1): direct API healthy, web failed HTTP readiness because Next CLI ran in monorepo root without app directory. Independently reproduced locally (exit1, missing root .next) and reviewer identified same. Fixed explicit start apps/web directory; local corrected startup on3002 and /status200 confirmed. Server logs attached to CI artifacts for failures. Next exact-head CI still required.

W00 final gate: Actions38066767207 and38066764096 SUCCESS on exact head185425a108c614b4022c07a6860b956900058b88, including post-job cleanup. PR #1 merged62fe10c. W01-A tests not run yet.

## W01-A work in progress
- `uv run --project apps/api python scripts/test_nutrition_contract.py`: exit0,4 tests (unknown/required fields, true0, exact fractions, invalid/negative/precision, positive energy).
- `uv run --project apps/api python scripts/validate_kit.py`:149passed0failed0skipped after schema change.
- `make backup-test`: exit0; consistent exported PG snapshot → encrypted dump → restore → all2 tables/6rows equal. This run is before W01 private tables; private-record proof still pending.

### W01-A integrated API/web checks
- `make install migrate openapi check-contract`: exit0; frozen locks, dev migration0002 and exact generated OpenAPI.
- Initial integrated Ruff: exit1 due QA import ordering; QA follow-up df5e968 fixes it, rerun below.
- `make test migration-test` before new QA races: exit0,56pytest20.95s +integrity1+contract4, real disposable migration roundtrip.
- After QA race/transport test integration: `make test`: exit0,59pytest25.59s no skips (25 independent QA cases), integrity1 and contract4 PASS.
- `make lint typecheck build`: exit0; Ruff/eslint, mypy24sourcefiles, tsc, production Next build (11routes).
- Independent security27 disposable-PG checks PASS; actualUvicorn productioncookie+40peerlimit despite changingXFF+5sbodydeadline PASS; pip-audit no known vulnerabilities after Argon2.
- Independent reviewer fixes incorporated: immutable UPDATE/DELETE guards; client retry retains key until decoded success; two distinct accounts/sessions race same target/slots with200+409 exactlyone mutation, sameactor2sessions createkey exactlyonce. Actual browser transportfault proof pending.

### W01-A actual Docker/browser/restore feedback loop
- `make dev`: exit0; nonroot API/Next + PostgreSQL healthy; frozen runtime Argon2 installed, DB migration0002; first download took4m09s, no failure. Real ready200, private session401 unauth, /household200.
- First `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit2,12passed/2failed9.9s; test helper eagerly read nonexistent logout204body. Fix QA12a36ef preserves status/no-store and removes only irrelevant body-read. Actions38074465454/38074462843 on067c268 failed same helper, all previous gates passed.
- After fix, full `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit0,14passed9.0s (officialChrome156), mobile390×844/desktop1440×900. Actual register→login→household→secondmember→distinctexactnull/zero goals→history→repeat/slot edits→reload→logout401; real committed POST/truncated JSON retry samekey creates exactlyone member; private cache excluded.
- Independent QA browser:4passed7.1s systemChromium153, own/tmp evidence/log; screenshots viewed and nooverflow/JSerrors. Root also viewed both complete household screenshots.
- After securityepoch/keyguard, root `make lint typecheck build`: exit0 again.
- `make backup-test`: exit0, real encrypted/authenticated dump with exported snapshot; disposable restore all11tables/224rows equal, including actual synthetic private target/history/session/audit/idempotency rows. Temp plaintext/backup/database removed.
- Security actual duplicate bound-email probe found PG DETAIL privacy leak (P2). Compose PostgreSQL terse/panic/0 settings fixed; own security repeat confirms sentinel absent. `make privacy-test`: exit0, genuine UNIQUE error logged and private bound sentinel absent; no private payload print. CI adds same dedicated service probe.

Final exact-head CI after helper/privacy fix still pending; wholeW01 remains incomplete (B/C).
