# WAVE-01: Households, profile kalorii i 5 posiłków

- **Owner(s):** backend + frontend + qa
- **Dependencies:** WAVE-00
- **Status:** IN PROGRESS — A merged (PR #2); invitations B local gates passed (PR #3 final CI/merge gate), original catalogue C remains

## Implementation checklist

- [x] Build password/session authentication, household membership and guest profile (no login for guest); A merged, B local83API/16E2E gate passed.
- [ ] Implement 2 sample members only as seeded demo data (2700 and 1600 kcal), all targets editable (kcal B W T), history versions.
- [x] Create 5 editable daily slot presets, repeat breakfast/dinner controls, Polish onboarding, mobile/desktop dashboard (A, real PostgreSQL and 390/1440 E2E).
- [ ] Create first ORIGINAL recipe fixtures/seed with real amounts and user-editable instructions; incomplete nutrient data visible as unknown.
- [x] Household IDOR tests and profile warnings for kcal-macro inconsistency (A; exact Decimal and strict 5% boundary).

## Acceptance gates

- [x] Two users with separate household records cannot read each other by guessing id (A API/QA tests).
- [ ] Changing profile goals updates preview, retains history.
- [x] 5 slots/day render on 390px and 1440px (A screenshots and E2E).
- [x] Repeat breakfast/dinner option visibly functional, not static toggle (A persisted preferences; planner reuse remains W03).

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
