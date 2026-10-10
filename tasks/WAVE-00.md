# WAVE-00: Bootstrapping i running baseline

- **Owner(s):** architect + backend + frontend + qa
- **Dependencies:** Brak (pierwsza fala)
- **Status:** LOCAL GATES PASS; PR #1 final CI/merge pending

## Implementation checklist

- [x] Create real monorepo: pnpm workspace for Next.js, uv/pyproject for FastAPI, domain package layout per ARCHITECTURE.
- [x] Implement /health and /ready, Next.js PWA shell and Polish nav; configure PostgreSQL/Alembic; developer Docker Compose with API/web + data stores.
- [x] Set migrations and demo fixture seeds, test framework pytest/Playwright, typecheck, eslint/ruff, GitHub CI with real commands.
- [x] Define Makefile dev/test/e2e/typecheck/lint/migrate/backup targets, not stubs.
- [x] Create docs/IMPLEMENTATION_STATUS.md, docs/TEST_REPORT.md, docs/EXECUTION_PLAN.md updates.

## Acceptance gates

- [x] Fresh checkout (with secrets configured) starts backend+frontend+DB and health page via make dev.
- [x] Migration up/down/up works on disposable DB.
- [x] Auth must never leak raw secrets.
- [x] At least 1 API integration + 1 browser smoke test pass; no fake green.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
