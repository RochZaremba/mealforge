# WAVE-02: Receptury, importer linków, nutri-data

- **Owner(s):** integrations + nutrition + backend + reviewer
- **Dependencies:** WAVE-01
- **Status:** IN PROGRESS — A private link-only runtime locally accepted in PR5 (247API/28E2E); final CI/merge pending. Parser/nutrition engine/providers not implemented yet

## Implementation checklist

- [ ] Canonical recipes/versions/sources, tag/storability/allegens models.
- [x] Implement link-only save for Mealime / Ani Gotuje / Kwestia Smaku without network fetch; exact canonical domain classification from registry (W02-A local gates PASS; final CI/merge pending).
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
