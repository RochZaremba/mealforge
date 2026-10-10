# W01-C review — private recipe catalogue

Date: 2026-10-11 (Europe/Warsaw). PR4: https://github.com/RochZaremba/mealforge/pull/4. Source reviewed70127bf; browser-only follow-upc880c5b. No production deployment.

## Scope and evidence

Private household recipe create/read/versioned edit/history, bounded list/history pagination, explicit separate demo, shared ephemeral authenticated household selection. Server-controlled rights/provenance; all snapshots remain drafts outside the planner. No URL fetch, nutrient engine, allergen verification, storage validation, inventory or plan operations in this slice.

Nutrition: independent70DTO/source assertions and3actual PostgreSQL tests PASS. All13original quantities/states preserved; missing nutrients/provenance/allergens/yield/time/storage/prices remain unknown; ml/piece not converted; demo2700/1600 with null macros preserves real profile columns and history.

Integrations: independent59provenance assertions and5runtime fixture tests PASS; original MealForge CC0 scope only text, user edits private/unknown license and immutable original lineage. No external fetch activated. Lead installed asset+audited loader and actual Docker equality gate PASS.

Security: independent26DTO+72isolated PostgreSQL assertions PASS. Household scope/current roles/replay, protected input fields, finite UTF-8 budgets, reference-only idempotency, immutable history and deferred composite current-version FK, demo rollback and fixture drift checked. Final root120API tests PASS without skips. Private PostgreSQL log probe PASS. Populated encrypted restore14tables1464rows PASS (counts only).

Independent reviewer: source PASS70127bf with no remaining P0–P2 finding in examined scope. Local final8Cbrowser tests PASS13.0s on mobile/desktop, followed by full24regression PASS27.1s. Exact final-head CI still required.

## Review fixes and retests

- Audited loader used snapshot DTO names when reading fixture time/price fields, causing demo503. Corrected mapping; valid3snapshots and missing/tamper/oversize tests pass.
- Legacy stored household/target results lacked additive source. Truthful pre-demo defaults plus actual persisted-result replay/revocation test pass.
- Stale A members/targets could show after switching to B; reads bound to loaded household and delayed add-member callbacks bound to captured household/auth generation. Actual committed-but-delayed response test passes, B IDs unchanged.
- Focus revalidation unmounted and discarded recipe draft. Retain scoped component hidden/inert until authorization returns; actual draft text/amount/attestation preservation passes.
- Confirmed role downgrade left an open recipe editor active. Current `can_edit` gates recipe and target forms; actual editor→viewer focus regression passes. Revoked save404 removes form/detail/cards.
- Approved query parameters were attached only to a configuration-check URL. Actual fetch URL now receives them; browser verifies distinct list/history pages and query rejection.
- First browser run failed4tests on exact nested textarea label matching. Accessible textbox selector fixes the harness; all8Ccases pass, including original assertions.

## Gate status

Independent reviewer LOCAL integration PASSc880c5b after personally viewing mobile detail/pagination and desktop detail/viewer. Lead accepts the local120API/24E2E, migration, installed/Docker fixture, populated restore/privacy and lint/types/build gate. No open P0–P2 finding in reviewed scope. Final exact documented-head GitHub Actions including cleanup remain required. W01-C/W01 cannot be marked complete or merged before those results. Full product flow through planning, guests, batches, shopping and inventory remains unimplemented.
