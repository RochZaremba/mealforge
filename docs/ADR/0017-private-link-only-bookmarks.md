# ADR-0017 — Private link-only recipe bookmarks

- Status: Accepted for W02-A after W01 gates/PR4 merge.
- Date: 2026-10-11.
- Extends:0003,0004,0005,0012,0016. No existing accepted decision is weakened.

## Decision

A saved URL with a user's own label/note is a household-scoped source bookmark, not a recipe candidate. Separate create-only immutable `recipe_links` records preserve actor/time/source classification, `link_only`, unknown license and `planner_eligible=false`. They create no recipe/version/nutrient/profile rows. Matching a known domain never confers article rights or fetch permission. Own contribution confirmation concerns only the user's label/note. No article, image, inferred title, macro, serving, allergen or safety claim is fetched or extracted.

GET list/detail and POST create use current household authorization, CSRF/origin, audit and reference-only idempotency. Unique `(household_id,canonical_url)` rejects duplicates with409; same-key replay returns the original201 after current authorization. Bounded pages and existing16KiB request/262KiB proxy budgets apply. No edit/delete/archive endpoint or pretend control in A; later lifecycle changes need their own audited contract.

Pure URL validation is packaged within the modular API at `mealforge.importers.url_policy`, exclusively owned by integrations. Existing `packages/importers` remains boundary documentation; no new framework/package dependency, runtime `sys.path` fallback or duplicate implementation. Backend loads the whole bounded registry with `importlib.resources`; CI and Docker compare it to root configuration. Classification is frozen on the bookmark, while any future remote importer must independently recheck current rights and networking constraints.

HTTPS only, no credentials or non443port. Reject controls/backslashes before parsing, malformed percent sequences, private/local host suffixes and browser-style numeric/IP hosts. Support strict IDNA round-trip without domain-changing mappings; canonical ASCII host, one optional terminal DNSdot removed, empty path `/`. Preserve encoded separators, path meaning and query order. Validated opening URL preserves fragment; canonical identity removes fragment only for deduplication. Bound UTF8 bytes before and after encoding to2048. Public recipe domains beyond the registry can be saved with unknown source; no DNS lookup, redirect or fetch occurs. This is bookmark shape validation, not proof of a public resolved IP or an approved future fetch.

Frontend uses literal escaped labels/notes and explicit plain external anchors with `target=_blank`, `rel=noopener noreferrer`; no image, script, preview or prefetch. UI states unknown nutrition/allergens and exclusion from the planner. Text such as “0 kcal”, “bez glutenu” or “pasteryzowane” remains a note and never becomes structured nutrition/safety data. Household selection remains ephemeral and server authorization stays authoritative.

## Verification and limits

Real PostgreSQL duplicate/concurrent-create/replay/access/audit/immutability and profile-preservation tests; pure hostile URL corpus; network/DNS spies prove zero outgoing work for known and unknown sites; browser390/1440 create/read/reload/pagination/viewer/revocation/cache tests. Existing120API24E2E regressions, migration/contract/lint/types/build/Docker/registry equality/restore/privacy and independent reviews plus exact-head CI are required. JSON-LD parser, remote providers, nutrient engine, normalization and full W02 remain unimplemented until later slices.
