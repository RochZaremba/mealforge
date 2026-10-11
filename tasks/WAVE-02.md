# WAVE-02: Receptury, importer linków, nutri-data

- **Owner(s):** integrations + nutrition + backend + reviewer
- **Dependencies:** WAVE-01
- **Status:** IN PROGRESS — A link-only PR5 mergeddb2d5ab; B1 own JSON-LD transient preview PR6 merged539ab2c after exacta4bf645 CI PASS. B2 own-author persistence LOCAL PASS (final CI/merge pending); normalization/nutrition/providers remain incomplete

## Implementation checklist

- [ ] Canonical recipes/versions/sources, tag/storability/allegens models.
- [x] Implement link-only save for Mealime / Ani Gotuje / Kwestia Smaku without network fetch; exact canonical domain classification from registry (W02-A PR5 merged; gates PASS).
- [ ] Implement local JSON-LD parser on user supplied data incl @graph, recipeYield, Instructions, units; importer draft with quality status.
  B1 preview and B2 bounded own-author persistent draft with immutable origin have local acceptance. Unit normalization and final integration gates remain, so this full item is not checked.
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
