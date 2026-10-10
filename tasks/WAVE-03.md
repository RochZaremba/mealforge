# WAVE-03: Dynamiczny tygodniowy plan, eventy i undo

- **Owner(s):** backend + frontend + nutrition + qa
- **Dependencies:** WAVE-02
- **Status:** NOT STARTED (initial kit)

## Implementation checklist

- [ ] Implement 7 day x 5 meal slots, pinned repeats breakfast/dinner, events participants/guests/no cook/eat-out.
- [ ] Implement preview/commit snapshot, versions with expected_version, lock, per-member grams and extras.
- [ ] Manual select/swap, random and suggestion candidates filtered by hard restrictions, atomic undo/redo/version trail.
- [ ] Recompute shopping demand (not yet purchased/committed) from plan; show preview deltas.

## Acceptance gates

- [ ] A 2700 B 1600 not mixed; no phantom exact nutrient values.
- [ ] Guest count Saturday lunch increases only lunch demand.
- [ ] Swap+undo keeps plan and dependents consistent (with immutable audit).
- [ ] No-cook day generates no cooking session; e2e full flow.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
