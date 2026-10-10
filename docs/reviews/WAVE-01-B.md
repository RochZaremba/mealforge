# W01-B review — single-use invitations and account access

Local integrated gates passed. Exact-head CI is required before PR #3 merge; this slice does not complete W01-C or the product.

## Findings and corrections
- P1 stale invitation ORM after waiting for a household lock could accept a revoked invitation or consume twice. Backend now peeks scalar IDs and refreshes locked rows; QA forces both recipients to wait before unlock, and revokes after the initial peek. Exactly one acceptance, or410/no link after revocation, is asserted in actual PostgreSQL.
- P2 household listing could expose stale editor capabilities after a downgrade. Current membership reload uses populate_existing; held-lock role-downgrade regression returns viewer capabilities. A queued target write after access revocation returns404 without target changes.
- P2 React sibling-key collision between invitation manager and slot editor retained multiple invitation forms/duplicate IDs after target edits. Distinct member-/invite-/slots- keys fix reconciliation; actual mobile/desktop E2E asserts one form and unique IDs after two edits.
- P2 test evidence could disclose codes through Playwright secret-action diagnostics or failure snapshots. B traces/failure screenshots are disabled; native secret entry avoids logging action values, code outputs are hidden/cleared before snapshots, and boolean-only log scans show no codes. Client retry memory stores SHA256 body fingerprints rather than raw accept codes.
- Unsupported Pydantic Rust-regex lookahead was fixed before integration. QA audit assertions now require exactly one invitation.accepted and one member.access_linked event per winning atomic transaction;409 OWNER_ACCESS_PROTECTED is the documented domain conflict. No invariant was removed.

## Evidence
- Root83pytest PASS80.23s, no skips; includes59A,6backendB and18independentQA B tests. Actual disposable PostgreSQL, not mocked locking. Integrity1 and target-contract4 PASS.
- Root full16 official Playwright tests PASS17.2s against nonroot Docker API/Next/PostgreSQL; mobile390 and desktop1440. Independent final B2flows PASS8.9s. Owner invite→recipient account→existing profile/viewer→403 write denial→owner revocation→private404/empty household list; targets/history remain.
- Ruff/eslint/mypy27files/tsc/build, OpenAPI drift, migration up/check/seed/down/up/check/schema equality and151kit checks PASS.
- Independent security51PG checks plus current-code/log/DB JSON exposure scan PASS; source review confirms owner protection, token expiry/rotation, current authorization on replay and no raw codes in persistent state.
- Independent nutrition27PG assertions PASS: exact Decimal/null/zero values, profile/member IDs, versions and history unchanged across link/revoke/restore; resident remains active, guests cannot gain accounts.
- Actual consistent encrypted backup→verified decrypt→disposable restore: all12tables/554rows equal, including populated invitation/profile/audit/idempotency tables. Genuine PostgreSQL UNIQUE error privacy probe PASS.
- Sanitized synthetic screenshots: docs/evidence/wave-01-b. Root viewed mobile viewer and desktop owner; QA viewed all six. No external fetch, email sending or production deployment.

## Remaining scope
Original private recipes/demo seed are W01-C. Nutrition engine/allergens/imports W02, plans/undo W03, kitchen/inventory/shopping W04, solver W05 and private offline queue W06 remain unimplemented. Public offline fallback is not private offline synchronization.
