# WAVE-01: Households, profile kalorii i 5 posiłków

- **Owner(s):** backend + frontend + qa
- **Dependencies:** WAVE-00
- **Status:** IN PROGRESS — A merged (PR #2); B merged (PR #3); C local120API/24E2E gate PASS, draft PR #4 final CI pending

## Implementation checklist

- [x] Build password/session authentication, household membership and guest profile (no login for guest); A/B merged;83API/16E2E gate passed.
- [x] Implement 2 sample members only as explicitly confirmed separate demo (2700 and 1600 kcal; all macro null), targets editable with history; actual C API/browser PASS, final CI/merge pending.
- [x] Create 5 editable daily slot presets, repeat breakfast/dinner controls, Polish onboarding, mobile/desktop dashboard (A, real PostgreSQL and 390/1440 E2E).
- [x] Three ORIGINAL recipe fixtures with13declared exact amounts and versioned user instructions; missing nutrient/allergen data visible as unknown; installed/Docker asset checks and actual API/browser PASS. These are drafts outside the planner.
- [x] Household IDOR tests and profile warnings for kcal-macro inconsistency (A; exact Decimal and strict 5% boundary).

## Acceptance gates

- [x] Two users with separate household records cannot read each other by guessing id (A API/QA tests).
- [x] Changing profile goals updates persisted household/Today target preview and retains history (A/C gates). Meal-plan preview remains W03.
- [x] 5 slots/day render on 390px and 1440px (A screenshots and E2E).
- [x] Repeat breakfast/dinner option visibly functional, not static toggle (A persisted preferences; planner reuse remains W03).

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
