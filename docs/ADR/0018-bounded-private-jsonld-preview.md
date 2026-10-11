# ADR-0018 — bounded private own JSON-LD preview

- Status: Accepted (W02-B1; save remains B2)
- Date: 2026-10-11
- Owner: lead; integrations/backend/nutrition/security read-only preflight

## Decision

Extend ADR0003/0004/0005/0012/0016 with a transient authenticated household preview of the user's own JSON-LD. B1 does not persist an import or create/edit any recipe. This separation prevents an import from being falsely recorded as manually entered content before immutable source-origin persistence is designed in B2. No existing snapshot or DB schema changes.

POST `/api/v1/households/{id}/recipe-imports/preview` requires editor/owner, trusted Origin, JSON, session CSRF and explicit `rights_attestation: i_am_author`. Input `document` is a string of strict JSON, at most12288UTF8bytes within the existing16KiB transport limit. Non-author/licensed imports, HTML extraction and network adapters remain unavailable. Preview is a bounded read computation: no idempotency record, audit write or source material persistence; no save/success toast.

Pure parser: stdlib JSON only, no context expansion, reference resolution, HTML/script execution or DNS/HTTP. Bound depth32 before decoding, nodes2048, numeric token64characters/exponent100, duplicate keys/nonfinite values/surrogates rejected. Exactly one inline Recipe node, found in a document/list/@graph; ambiguous multiple recipes rejected. Accept canonical schema.org type spellings, inline string instructions or HowToStep/HowToSection. Missing fields and unsupported reference-only instructions fail422, never silent truncation or guessed text. Limits title160, ingredients1..40 literal strings<=500, instructions1..30<=500 with bounded section names and yield1..8 literal declarations<=500. Payload limits apply also to ignored fields.

Schema semantics checked against primary [Recipe](https://schema.org/Recipe), [HowToSection](https://schema.org/HowToSection) and [HowToStep](https://schema.org/HowToStep) documentation on2026-10-11. This supports a deliberately bounded inline subset, not a complete JSON-LD expansion processor.

Preview preserves literal ingredients and section paths. Amounts/state/units remain unknown; no unit conversion or ingredient match. `recipeYield` is separately labelled unverified text, including numeric declarations; never inferred personal servings or measured cooked mass. Source `nutrition`, times, diet/storage claims, author/license/URLs/images are not promoted to calculated or verified values. Returned nutrients/allergens unknown, license null, planner false, status draft, persisted false; fixed warnings disclose ignored declarations. Server calculates exact source SHA256 and parser version for the transient preview; neither implies rights verification.

UI uses React escaped text, no images/anchors generated from the document and no browser persistence. Current household/auth generation/mounted guards bind the result; focus revalidation preserves scoped draft hidden/inert, confirmed loss of edit rights hides and unmounts form. No major dependency. Full W02 and JSON-LD save remain incomplete after B1.

## Verification

Pure schema.org fixtures plus adversarial duplicates/depth/nodes/nonfinite/Unicode/@context/script/ambiguity/size tests; outbound spies; actual PostgreSQL/current role/IDOR/CSRF/no persistence checks; mobile390/desktop1440 real preview/error/draft retention/unknowns/privatecache/no outbound; regression/static/OpenAPI/Docker/restore gates. Independent final review is required before merge; if agent resource limits prevent review, keep PR draft with that explicit limitation.
