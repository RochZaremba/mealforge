# W01-A review record (in progress)

Scope: real server sessions, household onboarding, non-login second member/guest, exact nullable targets/history, editable slots/repeat. Invites/recipes are B/C, not complete.

Independent security: live disposable PostgreSQL27checks, actual Uvicorn productioncookie/rate XFF spoof resistance/bodydeadline probes PASS. No known dependency vulnerabilities after Argon2. Root backup snapshot design accepted by security and reviewer; private-record restore runtime pending.

Nutrition:33 exact Decimal/unknown/zero/warning/share assertions PASS; future valid_from bug found and fixed by rejecting future local dates. API tests verify local timezone edge, target history and Atwater >5% warning without overwriting input.

QA:25 real-PG cases PASS independently and in integrated59pytest; two-account IDOR, CSRF, role/guest, foreign IDs, logout/replay, version races distinct actors and idempotency race distinct sessions. E2E two scenarios each mobile/desktop authored (full onboarding and real-commit/truncated-JSON retry), runtime pending.

Reviewer findings: P1 createhousehold replay exposed stored result after revoked access (fixed+QA regressions); P1 client cleared key before JSON decode could duplicate real committed mutation (fixed, live transportfault E2E pending); P2 immutable history DELETE guard absent (fixed+DB assertions); P2 race test used same session and serialized too early (new distinct actors/sessions tests PASS). Socket peer trust corrected with --no-proxy-headers in every launcher. Strong production config, bounded body/Argon2/auth DB counters, no private worker cache, no external recipe fetch.

Final combined Docker/browser/backup/CI gate still pending. No whole-W01 approval or production deployment.

Final local gate: root59API/migrations/lint/types/build PASS; full14officialChrome Docker E2E PASS9.0s and independentQA4systemChromium PASS7.1s. Actual all11tables/224rows encrypted snapshot restore PASS. P2 PostgreSQL bound-email DETAIL leak discovered during final review, fixed explicit terse/panic/0 server logging; real privacy sentinel re-probe PASS both security and root. Production DB settings documented, no deployment. Exact final CI head pending before merge.
