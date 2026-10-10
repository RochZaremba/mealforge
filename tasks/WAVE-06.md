# WAVE-06: PWA offline, feedback i release hardening

- **Owner(s):** frontend + backend + security + reviewer
- **Dependencies:** WAVE-05
- **Status:** NOT STARTED (initial kit)

## Implementation checklist

- [ ] Offline cached last plan/recipes/list, pending mutation queue with idempotency and version conflict UI.
- [ ] User ratings/rejections/preferences, explainability and reset/opt-out; no automatic allergy/target changes.
- [ ] Health/privacy export/delete, audit, security hardening, reproducible backups/restores, tests CI.
- [ ] Polish UI design polish, accessibility, kitchen timers, mobile install and remote preview.

## Acceptance gates

- [ ] PWA shows last synchronized plan while offline, writes show pending/not fake saved.
- [ ] Backup/restore test actually executed.
- [ ] Security review has no unresolved critical/high issues.
- [ ] Full A01–A15 E2E where applicable.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
