# Test report — 2026-10-11

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

W01-C final gate: exact13c1c834b5d3ea1484830fe1aa8af9fb08382d2f Actions38091280517+38091277922 SUCCESS, including120API/24E2E and cleanup. PR4 mergedc3f58ee7721595a21318b7ca71437ec1c91fd13f at2026-10-10T22:28:11Z (2026-10-11 Europe/Warsaw). WholeW01 COMPLETE. W02 has no runtime implementation yet; after main pull `make validate-kit`: exit0,154passed/0failed/0skipped before new contracts.

## W02-A integrated gate (in progress)

- `uv sync --directory apps/api --frozen; make validate-kit openapi`: exit0;156kit checks/no skips, generated actual OpenAPI includes link routes/strict DTOs.
- `make lint typecheck check-contract build`: exit0; Ruff/eslint, mypy42files, tsc, exact schema drift and Next production11routes PASS. Owned new browser lint/typecheck also PASS.
- `uv run --directory apps/api python ../../scripts/check_recipe_sources.py`: exit0; installed registry equals root and audited loader. Additional actual script probes reject modified package, changed loader and enabled-fetch configuration without exposing data.
- `make dev`: exit0;3healthy Docker services, actual migration0005. `make source-registry-test recipe-fixture-test`: exit0; actual container registry and original recipes equal installed/root resources, all external fetch remains disabled.
- Backend isolated full regression245tests PASS123.45s; this run collected older27QA cases. Latest independentQA29tests separately PASS29.46s. Root combined247tests/migration round-trip currently running; no success claimed yet.
- Independent source/security/nutrition/integrations checks in `docs/reviews/WAVE-02-A.md`; root real28mobile/desktop browser cases, populated15-table restore/privacy and exact-head CI still pending. No production deployment; parser/nutrition/provider functionality not implemented in A.

### W02-A final local feedback loop

- `make test migration-test`: exit0; **247pytest PASS142.50s/no skips**, backup integrity1 and nutrition contract4 PASS, both installed registry/original fixtures PASS. Actual disposable up/check/seed twice/down/up/check/schema equality PASS.
- `docker compose ... up --build -d --wait web`: exit0 after small URL.trim() form correction; final actual production Docker API0005/web healthy. `pnpm lint; pnpm typecheck`: exit0 on integrated browser/trim source.
- `PLAYWRIGHT_NO_SERVER=1 make e2e`: exit0; **28tests PASS27.0s**, official bundled Chrome,1440×900 and390×844. Full W01 regressions plus source-link save/reload/pagination, literal/XSS-shaped note, unsafe private-host422 retaining draft, viewer403/revoke404, no remote requests or private cache, delayed committed A201 cannot populate selected B.
- Root and independent reviewer personally viewed synthetic mobile/desktop screenshots now in `docs/evidence/wave-02-a`. No horizontal overflow or JS errors in scenarios. UI clearly states unknown nutrients/allergens, excluded planner and source rights unknown.
- `make backup-test privacy-test`: exit0; actual consistent exported snapshot → authenticated encrypted pg_dump → verified decrypt → disposable pg_restore: **15tables/2110rows** fingerprints equal including real synthetic source-link rows. Bound private UNIQUE parameter absent from DB logs, actual generic error present. Temporary plaintext/backup/test DB removed.
- Independent LOCAL reviewer PASS; source accepted at **8e4dbb19ec6b3a0795655a2d4902cbabe8e2d181** after actual browser/evidence review; no remaining P0–P2. Independent security/nutrition evidence above. PR5 https://github.com/RochZaremba/mealforge/pull/5 is draft until exact final documented-head GitHub Actions pass. Full W02 remains incomplete; no parser/nutrition/provider import or production deployment.

W02-A gate CLOSED: PR5 mergeddb2d5abaccaf46f3da4fe4ac7d025a491fe174e3 after exact4c81b0b90f2e6a98618edf07e78bfa3c82fc59ed Actions38092376097/38092372971 SUCCESS includingcleanup. No admin/bypass or production deployment. Full W02 remains IN PROGRESS.

## W02-B1 transient own JSON-LD preview (acceptance in progress)

- Bootstrap `make validate-kit`:156PASS/no skips before actual endpoint/schema changes. A separate system-Python command returned153PASS/1skip because jsonschema unavailable; this is not the kit gate. uv environment installs locked validation dependencies and passes the complete checks.
- `uv run --directory apps/api --env-file ../../.env pytest tests/test_jsonld.py tests/test_jsonld_preview.py`:53PASS4.99s; strict shape corpus, finite bytes/depth/nodes/numbers/duplicates/Unicode, schema.org graph/types/sections/yield, zero DNS/HTTP and actual scopedPG authorization/no persistence. Strengthened populated existing recipe/version/profile including exact100.125 andtrue0 snapshot test:3PASS5.88s.
- Initial mypy rejected str default for Literal parser version; corrected explicit Literal constant. `make lint typecheck check-contract build`:exit0; Ruff/eslint/mypy44/tsc/OpenAPI/production11routes PASS. Owned53 targeted tests and independent reviewer50pure tests PASS0.14s. New API follows transient ADR0018, no save or DB migration.
- First full `make test migration-test`:exit2;299PASS/1failure169.81s. Obsolete health assertion prohibited every import route; changed to assert ONLY implemented preview is present and future planner/imports absent. Corrected12health tests PASS2.00s. Full300 final rerun in progress; no full success claimed yet.
- `make dev`:exit0; actual3healthy Docker services with new preview route and existing0005schema. `PLAYWRIGHT_NO_SERVER=1 make e2e`:30PASS38.5s actualofficialChrome390/1440; ownJSON-LD preview/error/draftfocus/literalmarkup/yieldunknown/no remote requests and lateA200 not shown underB, plusall28regressions. Final two targeted cases after screenshot-scroll/cache assertions pending.
- `make source-registry-test recipe-fixture-test backup-test privacy-test`:exit0; actual installed/Docker resources equal, encrypted exported-snapshot15tables2961rows restore fingerprints equal, actualPGprivate-bound-value log probePASS. Preview creates no source/recipe/audit/idempotency rows, and no snapshot migration is claimed.
- Independent reviewer SOURCE PASS with no openP0–P2 after actual pure50tests. Specialized B implementation agents hit resource-credit errors; lead implemented allB1files exclusively after read-only preflight. Full local/CI/review gate pending, no B1 completion yet; B2immutableimport persistence and nutrition/providers remain future slices.

### W02-B1 final local retests

- Final `make test migration-test`:exit0; **300pytest PASS184.40s/no skips**, backup integrity1/nutrition contract4, installed fixture/registry and actual disposable migration up/check/seed twice/down/up/check/schema equality PASS. The earlier health assertion failure is resolved; no test disabled or removed.
- Final `pnpm lint; pnpm typecheck; make validate-kit check-contract`:exit0; new browser/proxy/types and157kitchecks/no skips/drift PASS.
- Final targeted `... playwright test e2e/jsonld-preview.spec.ts`:exit0;2PASS4.4s after scroll-to-top screenshot correction and private-cache assertion, same390/1440 actualDocker. Full30PASS38.5s remains the regression run; only test evidence/assertions changed afterward, no app source change. Synthetic screenshots under docs/evidence/wave-02-b1; no secrets/codes or external recipe assets.
- Source3a2b387/doc45a724a; PR6 https://github.com/RochZaremba/mealforge/pull/6. Independent final LOCAL evidence review and exact final documented-head CI pending; B1 not marked merged/complete yet. FullW02/B2save/nutrition/providers/planning remain incomplete. No production deployment.

W02-B1 LOCAL gate PASS: independent reviewer personally read final logs and viewed both synthetic screenshots; source3a2b387/docsbaseline45a724a, no openP0–P2 in transient own-author preview scope. Earlier pending fields above are historical; all local gates are now complete. Intermediate exact45a724a241a98fab5aa1e3d53019a903117948bc Actions38129607272/38129577726 SUCCESS includingcleanup; final documented-head CI still required beforemerge.

W02-B1 gate CLOSED: exacta4bf645cb0c216d23feb5e34bde9eee5c4b7a16f Actions38129924542/38129922538 SUCCESS includingcleanup. PR6 merged539ab2ce0ef91809cc02490364ad824263cc7e4b at2026-10-11T09:56:53Z. No admin/bypass or production deployment. B1 COMPLETE within author-only transient preview scope; wholeW02, B2persistence/nutrition/providers and later domainflow remain incomplete.

## W02-B2 — acceptance in progress

- Bootstrap `python3 scripts/validate_kit.py`: exit0,154 checks PASS but one skipped fixture/schema check because system Python lacks jsonschema; not accepted as complete kit gate.
- Bootstrap `make validate-kit` with the locked uv environment: exit0,157 checks PASS/no skips, before B2 contracts and ADR changes.
- Execution plan4646eca, contract4d429fe, ADR0019; integrations/security read-only preflight accepted with current authorization/reparse/origin/budget/unknown constraints. Backend/frontend/QA assigned exclusive new worktrees/files. No B2 functionality or final test success claimed yet.

### B2 first integrated feedback loop

- Backend706073f + frontend609fe94 + QA dd6c25c/0b09ef6 integrated on lead122e608; actual OpenAPI generated. Targeted backend/QA23 PostgreSQL tests passed25.14s (including migration up/check/down5/up/check, immutable snapshots, duplicate races and origin/unknown preservation). Initial expression-index reflection drift was fixed using explicit PostgreSQL text[] cast; no check suppression.
- QA followup65d6f2a adds changed-payload retry409 and malformed/oversize HTTP rejection:15 isolated PostgreSQL tests PASS21.71s; Ruff PASS. The ongoing full test run collected323 before these two extra cases were integrated; its final result remains pending.
- First integrated `make lint typecheck check-contract build validate-kit`: exit0; Ruff/eslint/mypy46/TypeScript/OpenAPI/production11routes and158 kit checks/no skips PASS. `make dev`:exit0; actual API/web/PostgreSQL healthy, migration0006 installed. Final frontend guard patch/build still required.
- Independent reviewer found P2: an older pending recipe detail GET can overwrite the newly imported201 detail. Frontend fixes request-generation invalidation; QA adds an actual delayed-response regression. This issue is OPEN until patch and browser retest; B2 acceptance is not claimed yet.
