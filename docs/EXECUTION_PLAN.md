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

## WAVE-01-B: invitations and revocable account access
W01-A COMPLETE: PR2 mergedd544a88 after exact4eaf30c Actions38075073982/38075070579 PASS; local59API+14E2E+11-tablebackup, independentreviews accepted.

GoalB: owner creates24h one-use invitation, recipient joins with ownaccount and links existing second-person profile; owner can change editor/viewer or revoke access while keeping resident nutrition/active participation. No email sending. Original recipes remain C.

Ownership: backend branchbackend/wave-01-b owns apps/api/** except QA test_invitations_security.py; frontend frontend/wave-01-b apps/web/** except e2e/config; QA qa/wave-01-b ONLY apps/api/tests/test_invitations_security.py + apps/web/e2e/invitations.spec.ts; leadcontracts/docs/infra/generatedOpenAPI. Security/reviewer/nutrition read-only audit. Branch/worktrees start mergedA plus this plan; no shared edits/reverts.

Contract /api/v1: POST /households/{id}/invite {role:editor|viewer,member_id:UUID|null}; owner-only GET /households/{id}/invitations; POST .../invitations/{invitation_id}/revoke {expected_version}; POST /household-invitations/accept {token}; PUT .../members/{member_id}/access {expected_version,role:editor|viewer,access_enabled:bool}. All mutations CSRF+trustedOrigin+Idempotency-Key, locks/version/audit. Invite DTO hasid/role/member_id/expires_at/status/version; create returns one rawcode only to authenticatedowner, never URLs/log/audit/idempotencyJSON/list. Frontend copy only explicitclick (clipboard success only after confirmation), accept inputJSONbody, no outgoing messages. Owner-only controls hidden for editor/viewer; viewer readonly realprofiles/slots.

Persistence: migration0003 Invitation+member access_enabled defaulttrue/access_version default0. active remains resident participation; access_enabled controls accountauthorization separately. Guests neverlogin, owner cannot self-demote/revoke. Existing targets/history/member IDs preserved during link/revoke. Recheck everymembership/list/query/idempotency replay for revokedaccess. Tokens HMAC-derived from private randomnonce+UUID (separate domain) with SHA256 hash stored; idempotentcreate uses invitationref to regenerate, neverpersist rawcode. Secretrotation failsclosed mismatchedderivation. Accept exactlyonce and atomiclink+audi+idempotency; existingother-account memberlink conflict; guest/foreignmember forbidden; role changes/revocation version409.

Gates: PG TTL/reuse/revoked/guest/foreignmember/owneronly/accessrevocation/replay/rotation and two-accountconcurrentaccept; audit/records no rawtokens, profile unchanged. E2E owner invite→secondaccountregister/login→accept/linkprofile/targets→viewer read-only→revoke→private404 while owner still sees originalnutrition; mobile390/desktop1440; copiedcodes not sentexternally. Regression59API+14browser and migration/OpenAPI/lint/type/build/Docker/backup. Feedbackloop/finalsecurity/nutrition/reviewer/CIexact-head beforemerge. FullW01 incomplete untilC.
