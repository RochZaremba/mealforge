# WAVE-07: Duża biblioteka + pełna automatyzacja jakości

- **Owner(s):** integrations + nutrition + reviewer + ux
- **Dependencies:** WAVE-06
- **Status:** NOT STARTED (initial kit)

## Implementation checklist

- [ ] Build 100+ locally usable, original or properly licensed verified recipes; recipe seed generator must not fabricate data.
- [ ] Where legitimate, add Wikimedia cookbook adapter with detailed CC BY-SA/media attribution and separation; expand TheMealDB official API flows under terms; never mass scrape sites link-only.
- [ ] Add duplicate detection, collection quality score, import preview/manual corrections, import provenance audits, link cards for multiple Polish blogs.
- [ ] Instrument feedback loop into actionable but review-gated issue/PR pipeline; measure real planning/waste/usage.

## Acceptance gates

- [ ] 100 actually complete recipe versions validated, distinct, rights documented; no inflated records.
- [ ] External API outage leaves local catalog functional.
- [ ] Licensing audit and no protected content reproduction from restricted sites.
- [ ] User can save a URL from all listed sites, including unsupported, without fetch.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
