# ADR-0019 — persisted private own JSON-LD import origin

- Status: Accepted for W02-B2
- Date: 2026-10-11
- Owner: lead; independent integrations/security/nutrition preflight

Extends ADR0003/0004/0005/0012/0016/0018. B1 preview remains transient. B2 adds an explicit idempotent authenticated save of the user's own bounded JSON-LD into the existing private Recipe/immutable RecipeVersion catalogue. This is author-only private content, not a rights-verified third-party source or a permissioned fetch adapter.

Server reparses the submitted document with the strict pure B1 parser after current write authorization and CSRF/Origin checks. Client-supplied preview/provenance is forbidden. Initial snapshot source_mode is user_supplied_jsonld. Typed optional provenance.import_origin (legacy default null) stores SHA256 of the exact UTF8 document, parser version, importing account UUID/time, literal ingredients, steps with section paths, unverified yield and fixed ignored-field names. Raw documents, remote contexts/assets/URLs and source author/license/nutrition/storage values are discarded. SHA256 identifies bytes; it does not verify rights. The user attests authorship of the complete submitted recipe.

Manual edits are user_authored contributions with source-version lineage and retain original import_origin unchanged. Historical immutable snapshots are not rewritten. The origin is evidence of the original submission, never a claim that later instructions or amounts were parsed from that source. Existing immutable version triggers cover it; a separate source table is unnecessary for this restricted non-network author-only slice. Future external sources require their own rights/attribution model and ADR.

Migration0006 adds a partial unique expression index on household and original import hash for version1. Save serializes on the existing household lock and checks previous original imports; duplicate exact bytes with a new key yields409 JSONLD_ALREADY_IMPORTED. Same idempotency key returns original201 version after reauthorization even after manual edits. Different byte formatting may produce distinct recipes; similarity matching remains future work. Audit is metadata-only and idempotency holds version references, never document payloads.

Save respects existing catalogue bounds (ingredient160, title160, steps1..30 each500); incompatible previews fail422 without truncation. Full UTF8 snapshot budget, including duplicated immutable origin, is validated before INSERT to respect32KiB SQL bound. Unknown quantities/units/state, calories/macros/allergens, measured yield/servings, times/storage/prices remain unknown and planner_eligible false. Textual yield is labelled unverified and does not become personal portions or measured mass.

No new major dependency, network activity, global content publication, offline private cache or production deployment. Unit normalization and nutrient/provider engines remain separate W02 slices. Verification includes actualPG atomicity/concurrency/immutability/auth/replay/bounds, real390/1440 browser save/edit/history, no outbound/cache/log leaks, legacy compatibility, migration roundtrip and populated encrypted restore.
