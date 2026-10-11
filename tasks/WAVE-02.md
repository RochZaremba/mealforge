# WAVE-02: Receptury, importer linków, nutri-data

- **Owner(s):** integrations + nutrition + backend + reviewer
- **Dependencies:** WAVE-01
- **Status:** IN PROGRESS — A link-only PR5 mergeddb2d5ab after exact4c81b0b CI PASS. B1 own JSON-LD transient preview implemented, final gates in progress. Import persistence/nutrition/providers remain incomplete

## Implementation checklist

- [ ] Canonical recipes/versions/sources, tag/storability/allegens models.
- [x] Implement link-only save for Mealime / Ani Gotuje / Kwestia Smaku without network fetch; exact canonical domain classification from registry (W02-A PR5 merged; gates PASS).
- [ ] Implement local JSON-LD parser on user supplied data incl @graph, recipeYield, Instructions, units; importer draft with quality status.
- [ ] Create permissioned API adapter for TheMealDB behind source registry flag + credentials and a nutrient data provider abstraction for USDA/OFF (no unrestricted frontend calls).
- [ ] Build conversions/normalization/alias dictionary for Polish ingredients, traceable nutrient math with unknown-as-null.
- [ ] Implement product barcode search only when OFF terms accepted/configured, protect APIs and avoid license mixing.

## Acceptance gates

- [x] Network spy verifies zero outbound fetch for restricted site (actual API/PG and mobile/desktop browser; W02-A).
- [ ] Fixture sample schema.org recipe parsed correctly; unknown g->incomplete macro.
- [ ] API transport rejects SSRF, IP hosts and prohibited redirects.
- [ ] Import cannot silently put unverified candidate into optimizer.

## Evidence and integration

Update `docs/IMPLEMENTATION_STATUS.md` and `docs/TEST_REPORT.md`: command, exit status, fixtures, screenshots (if UI), missing cases, branch/commit, review findings. Stop before next wave if a critical invariant fails.

## Handoff

List added/changed files, schema migrations, explicit limitations, tests rerun, and next unblocked task.
