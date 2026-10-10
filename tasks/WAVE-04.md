# WAVE-04: Meal prep, słoiki, ledger magazynu, zakupy

- **Owner(s):** backend + frontend + qa + security
- **Dependencies:** WAVE-03
- **Status:** NOT STARTED (initial kit)

## Implementation checklist

- [ ] Cooking session and batch actual yield with 2-person grams; containers as optional volume_ml and net_g measured.
- [ ] Storability mode separation; fail-closed verified shelf-stable. Label generation incl QR to internal batch id; source and state.
- [ ] Inventory lots with ledger, FEFO, reservations, receive/consume/adjust operations, optimistic/version checks.
- [ ] Shopping demand minus available (unreserved) stock and already allocated batch portions; receipts add lots.
- [ ] Sync state across two household users.

## Acceptance gates

- [ ] 2 simultaneous consume requests: one succeeds, second 409.
- [ ] Volume_ml never assumed == mass_g.
- [ ] Non-verified chili jar does not become shelf-stable.
- [ ] Shopping uses available qty once; recipe batch consumption correctly updates stock.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
