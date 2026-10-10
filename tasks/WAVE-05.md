# WAVE-05: Optimizer, One-Click Week, Fridge Rescue

- **Owner(s):** nutrition + backend + frontend + qa
- **Dependencies:** WAVE-04
- **Status:** NOT STARTED (initial kit)

## Implementation checklist

- [ ] Choose deterministic solver OR-Tools CP-SAT based on realistic bounded model; implement fixed seed, time limits, explain infeasible.
- [ ] Hard constraints allergen, no cook, available portions, storage expiry, locked meals, attendees. Soft kcal ±5% and macros ±10%, preferences, price (only known), prep/waste.
- [ ] One Click Week preview+commit, favorite and random swap candidate UX, stock-aware recipes, FEFO food rescue.
- [ ] Regression test 2 persons, 5 meals, repeats, 8 portions requested 9, allergies, unknown nutrients.

## Acceptance gates

- [ ] Hard constraints never relaxed; explain infeasible instead of fake success.
- [ ] Same fixed-seed inputs yield same meal selection.
- [ ] Plan commit produces consistent shopping/reservation delta.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
