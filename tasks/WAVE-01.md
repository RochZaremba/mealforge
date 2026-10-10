# WAVE-01: Households, profile kalorii i 5 posiłków

- **Owner(s):** backend + frontend + qa
- **Dependencies:** WAVE-00
- **Status:** IN PROGRESS — slice A; invitations/original catalogue remain B/C

## Implementation checklist

- [ ] Build password/session authentication, household membership and guest profile (no login for guest).
- [ ] Implement 2 sample members only as seeded demo data (2700 and 1600 kcal), all targets editable (kcal B W T), history versions.
- [ ] Create 5 editable daily slot presets, repeat breakfast/dinner controls, Polish onboarding, mobile/desktop dashboard.
- [ ] Create first ORIGINAL recipe fixtures/seed with real amounts and user-editable instructions; incomplete nutrient data visible as unknown.
- [ ] Household IDOR tests and profile warnings for kcal-macro inconsistency.

## Acceptance gates

- [ ] Two users with separate household records cannot read each other by guessing id.
- [ ] Changing profile goals updates preview, retains history.
- [ ] 5 slots/day render on 390px and 1440px.
- [ ] Repeat breakfast/dinner option visibly functional, not static toggle.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
