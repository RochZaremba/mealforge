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

Final exact-head4eaf30c CI PASS: Actions38075073982+38075070579, including PostgreSQL privacy probe and14E2E. PR2 mergedd544a88. WholeW01 remains incomplete (B/C); B tests not run yet.

## W01-B integrated gate (in progress)

- `make migrate openapi check-contract`: exit0; real development migration0003 and generated OpenAPI match.
- `make test migration-test` before independent B QA integration: exit0;65pytest27.46s, no skips (59A+6B), integrity1 and target-contract4 PASS; disposable migration up/check/seed/down/up/check/schema equality PASS.
- Integrated web `pnpm lint && pnpm build && pnpm typecheck`: exit0;11routes; before final fingerprint-only retry fix. Final source needs browser/regression gate.
- Integrated API Ruff/mypy: exit0;27sourcefiles.
- Independent security:51actual disposable-PG checks PASS; expiry, rotation, reference-only idempotency, owner protection, revoked reads/list/replay, unchanged profiles. Client hashing/retry/auth-generation regression probes PASS.
- Independent nutrition:27actual disposable-PG preservation assertions PASS across accept/viewer/revoke/restore/guest denial. Exact targets, nulls, zero, member/profile IDs and history unchanged.
- Feedback loop: unsupported Pydantic Rust-regex lookahead prevented first independent test collection (exit2); backend replaced regex before integration. First combined agent run75/80 passed;5QA expectations corrected to assert both intentional metadata-only audit actions once each, and409canonical-owner protection. Corrected full test run pending; no failing invariant suppressed.
- Deterministic distinct-session concurrency, actual Docker/two-account mobile+desktop browser, restore, final reviews and exact-head CI remain pending. PR #3 is draft; B is not complete.

### W01-B full API / actual Docker gates
- `make test` after QAaf88b32 integration: exit0,80pytest40.95s, no skips; integrity1 and target-contract4 PASS. Fifteen independent B security tests include a real PostgreSQL row-lock barrier: two recipient requests complete lookup before unlock, then exactly one links a new resident (200/409).
- `make lint typecheck`: exit0 after final fingerprint-only client fix; Ruff/eslint/mypy27files/tsc PASS.
- `make dev`: exit0; nonroot actual API/Next/PostgreSQL healthy, migration0003 complete, Docker production build11routes. Public ready200 and unauthenticated private API401/no-store through the real proxy.
- `make backup-test privacy-test`: exit0;12tables/353rows consistent encrypted restore equal; actual UNIQUE error present without private bound sentinel. Invitation table exists; full live two-account invitation records and browser evidence still pending.

### W01-B browser feedback loop (gate remains open)
- Existing14A/W00browser regressions: `PLAYWRIGHT_NO_SERVER=1 make e2e` exit0,14passed9.8s against actual B Docker and final client fingerprint code.
- Intermediatebf0e3d8 CI Actions38076686593/38076684209 SUCCESS (80API +14oldE2E); new B browser cases were not yet integrated, so this is not the final B gate.
- First independent B two-account browser run: exit1,2failed at120s timeout selecting invitation member on both viewports. Actual DOM had repeated invitation sections/duplicate IDs. Root identified identical React sibling keys on InvitationManager and MealPresets; frontend fix and browser recheck pending. Tests will require exactly one invitation form rather than selecting the first duplicate. No raw codes are retained in browser traces/screenshots.

- Fixed source2a57017 actual `make dev` rerun: exit0; three distinct sibling-key namespaces and Docker production build11routes. `make validate-kit check-contract lint typecheck`: exit0;151kit checks, no failures/skips, OpenAPI exact, Ruff/eslint/mypy27/tsc PASS.
- Root `make test` afterd667a3a forced-interleaving tests: exit0,83pytest80.23s, no skips; integrity1 and target-contract4 PASS. Independent owned B security suite18passed27.58s.
- Second independent B browser run still failed2cases: DOM now has exactly one invitation form (source fix effective); exact getByLabel on a nested select includes option text. QA switching to accessible combobox names and shorter deadlines. Native secret entry successfully reached authenticated target version2; prior logs/error-context contain no64hex codes (boolean-only scans).

### W01-B final local gate
- New B QA `39428db` + screenshot-only `010b38c` integrated asf019092/5784c46. Independent2browserflows PASS9.0s, then8.9s after screenshot normalization; no overflow/JS errors. Traces absent, code-shaped strings absent from logs/context; six synthetic sanitized PNGs copied to docs/evidence/wave-01-b and reviewed.
- Root `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit0,16passed17.2s official bundled Chrome, actual Docker; includes all14A/W00regressions and2B two-account lifecycle cases.
- After actual B browser writes, `make backup-test`: exit0,12tables554rows exact; snapshot includes2actual invitation records plus42profiles/112audit/110idempotency rows. Counts only; no private values printed.
- Final local source review: docs/reviews/WAVE-01-B.md. Exact final-head CI remains merge gate; priorbf0 CI did not include new B browser cases.

W01-B final exact-headd650dd006ea62701ff2ef1bd4cd0b6442401c365 CI PASS: Actions38082688574+38082684928, including83API/16E2E and cleanup. Final root `make lint typecheck build`: exit0,27API sourcefiles/11web routes. PR3 merged7b1df55703acbff3a86c3a94ad725d85a0950678 at2026-10-10T20:13:46Z. W01-C starts only after this gate.

## W01-C worktree checks — 2026-10-11 (gate pending)

- `python3 scripts/validate_kit.py`: exit0,153passed/0failed/0skipped after original fixture integration. Lead plan/ADR0016 preceded production changes.
- Independent QA actual isolated PostgreSQL `tests/test_recipes_security.py`: exit0,25passed27.70s. Recipe create/update/history, household roles/revoked replay, Decimal rejection, composite FK and immutable snapshots, separate demo, concurrent retry and reachable pages checked. Commit68c5e8a; final regression fixes pending.
- Backend first combined new QA+W00 run:29passed30.58s; Ruff/mypy34 source files PASS. Final full regression not yet accepted: stale historical assertions required updates for newly implemented recipe routes and additive household source.
- Nutrition independent70DTO/source assertions PASS;3targeted actual PostgreSQL tests PASS4.90s. Thirteen exact amounts/states, unknown nutrients/allergens/yield/storage, no ml/piece conversion, unchanged real profile columns after explicit demo.
- Security independent26DTO+72actual isolated PostgreSQL assertions PASS. Viewer can create a separate owned demo; original CC0/private edit lineage, tenant/replay checks, strict input, immutable/deferred FK, fixture tamper/oversize fail closed. Final frontend acceptance remains open.
- Integrations independent59provenance assertions and5runtime fixture tests PASS. No activated external fetch; private user edits do not inherit CC0.
- Lead `uv run --directory /home/roch/programing/mealforge-worktrees/backend-c/apps/api python /home/roch/programing/mealforge/scripts/check_original_recipes.py`: exit0, root/installed fixture equality and audited runtime loader PASS. Docker C packaging not checked yet; current healthy containers still run B.
- Frontend review found/fixes in progress: late A member POST contaminating B view; focus destroying unsaved recipe draft; approved pagination parameters discarded before proxy fetch. Actual deterministic browser regression required for all three. No C mobile/desktop success claimed yet.

### W01-C integrated feedback loop

- Lead took over remaining worker edits after workspace credit errors interrupted backend/frontend/QA/security turns. Work preserved in separate branches; no concurrent file edits. Backend7eedeae, frontendca5bfef and QA68c5e8a/d2e1498/d5c9555 integrated on `feat/wave-01-recipes`; generated OpenAPIca45423.
- `make install migrate openapi check-contract`: exit0; frozen dependencies unchanged, real development migration0004, generated OpenAPI exact. `make validate-kit check-contract`: exit0,154kit checks, no failures/skips.
- `make test migration-test`: exit0,120pytest PASS115.13s, no skips (83regressions+37C); backup integrity1, target-contract4, installed original fixture/audited loader PASS; actual disposable PostgreSQL up/check/seed twice/down/up/check/schema equality PASS.
- `make lint typecheck build`: exit0; Ruff/eslint/mypy34files/tsc/production11routes; rerun after final capability guards and browser selector fix also PASS.
- `make dev` and final source rebuild: exit0; real nonroot API/Next and PostgreSQL healthy. `make recipe-fixture-test`: exit0; full original asset equals root and installed package, including actual Docker API image.
- First root `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit2,20passed/4failed38.8s. Actual forms retained their state and accessible textarea names were correct; `getByLabel(...exact)` incorrectly included nested textarea content. Fixc880c5b uses stable accessible textbox name. No runtime success assertion weakened.
- New C suite after fix: `PLAYWRIGHT_NO_SERVER=1 uv run --project apps/api --env-file .env pnpm --filter @mealforge/web exec playwright test e2e/recipes.spec.ts`: exit0,8passed13.0s official Chromium, mobile390×844/desktop1440×900. Actual separate demo and unchanged real target/history; create/edit/reload with exact amounts/unknowns; viewer→editor→viewer focus closes form; subsequent revoked mutation404 removes private state; late committedA201 cannot change B IDs; list/history pages reach every distinct item/version through proxy.
- `make backup-test privacy-test`: exit0; actual encrypted authenticated snapshot/restore all14tables1464rows equal, including live synthetic recipe versions/demo/profile/audit/idempotency data. Temp plaintext/disposable restore DB removed. Real UNIQUE error logged without private bound sentinel.
- Six synthetic sanitized screenshots in `docs/evidence/wave-01-c`; root viewed mobile detail and desktop viewer, overflow/page-error assertions passed. Original quantity/provenance review remains PASS; imports and nutrient calculation remain future work.
- Independent reviewer SOURCE PASS70127bf: earlier P2s resolved; retained recipe and target forms respect current edit capability. Final full24browser regression and exact-head CI pending. PR4 draft: https://github.com/RochZaremba/mealforge/pull/4.

- Final root `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit0,24passed27.1s, official bundled Chromium against actual C Docker; all16A/B/W00regressions and8Ccases. Initial Actions38090886410/38090835457 onca45423 failed the same nested textarea selector (logs confirmed); subsequentc880c5b CI and final documented head remain the merge gate. No checks skipped or production deployed.

- Independent reviewer LOCAL integration PASSc880c5b after viewing mobile detail/pagination and desktop detail/viewer; production source70127bf unchanged by harness fix. Lead accepts the local gate. Final documented-head Actions including cleanup remain required before merge.
