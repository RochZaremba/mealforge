# API v1 — kontrakty use-case

**Prefiks:** `/api/v1`. JSON; auth przez bezpieczne cookies lub sesję z CSRF policy. W odpowiedziach `problem+json` z `error_code`, `message`, `request_id`, `field_errors` (opcjonalnie). API generuje docelowy OpenAPI z kodu FastAPI. `contracts/openapi.yaml` jest generowane z działającego API; tabela docelowa poniżej zawiera również funkcje przyszłych fal.

## Mutations

- `Idempotency-Key` obowiązkowy dla commit plan, swap/undo, shopping receipt, inventory consume/reserve, batch create.
- `If-Match` / `expected_version` dla konkurencyjnych planów i stanów. 409 przy konflikcie.
- `household_id` występuje w ścieżce, lecz każde użycie podlega pełnej weryfikacji uprawnień.
- Wszystkie timestampy ISO8601 offset-aware; daty planów lokalne `YYYY-MM-DD` w strefie gospodarstwa.

## Core endpoints

| Method | Path | Opis |
|---|---|---|
| `POST` | `/auth/register` | utwórz użytkownika |
| `POST` | `/auth/login` | sesja + CSRF handshake |
| `POST` | `/auth/logout` | wygaszanie sesji |
| `GET` | `/households` | gospodarstwa dostępne po auth |
| `POST` | `/households` | nowy dom |
| `POST` | `/households/{id}/invite` | token zaproszenia w krótkim TTL |
| `GET/POST` | `/households/{id}/members` | osoby, goście |
| `PUT` | `/households/{id}/members/{member_id}/nutrition-target` | nowa wersja celów |
| `GET` | `/households/{id}/recipes` | validated recipes + saved external links filter |
| `POST` | `/households/{id}/recipes` | własny przepis |
| `POST` | `/households/{id}/recipe-links` | zapisz URL bez fetchu |
| `POST` | `/households/{id}/recipe-imports/preview` | dane użytkownika lub authorized-fetch, nigdy default fetch |
| `POST` | `/households/{id}/recipe-imports/{draft_id}/approve` | zatwierdzenie po walidacji |
| `GET` | `/households/{id}/plans/{week_start}` | 7 dni, 5 slotów, per-person portions |
| `POST` | `/households/{id}/plans/preview` | solver dry-run, return constraints/trade-offs |
| `POST` | `/households/{id}/plans/commit` | transakcja plan+reservations+shopping |
| `POST` | `/households/{id}/plans/{plan_id}/swap` | proposal + commit or preview flag |
| `POST` | `/households/{id}/plans/{plan_id}/undo` | compensating version |
| `POST` | `/households/{id}/events` | goście/no-cook/etc i replan preview |
| `GET/POST` | `/households/{id}/inventory/lots` | inventory |
| `POST` | `/households/{id}/inventory/transactions` | event reserve/consume/adjust |
| `GET` | `/households/{id}/shopping/{week_start}` | aggregated requirements |
| `POST` | `/households/{id}/shopping/{list_id}/receive` | purchase -> inventory lots |
| `GET/POST` | `/households/{id}/cooking-sessions` | session plan and status |
| `POST` | `/households/{id}/batches` | recipe version -> measured yield/portions |
| `PATCH` | `/households/{id}/batch-portions/{portion_id}` | move/freeze/consume with guards |
| `POST` | `/households/{id}/feedback` | opt-in rating / rejection |
| `GET` | `/health` | liveness |
| `GET` | `/ready` | dependency readiness |

## Przykład `nutrition-target` (dane demonstracyjne)

```json
{
  "kcal_target": 2700,
  "protein_target_g": 170,
  "carbs_target_g": 310,
  "fat_target_g": 85,
  "effective_from": "2026-10-12",
  "goal": "maintenance"
}
```

Przykład nie jest domyślną dietą użytkownika; UI informuje o ewentualnej niezgodności energii wyliczonej z makro i zadanych kcal (Atwater approx). Makro to precyzyjnie definiowane targety, a nie obowiązkowe proporcje 40/30/30.

## Przykład importu danych

```json
{
  "source_url": "https://example.org/recipe/1",
  "mode": "user_supplied_jsonld",
  "payload": {"@context": "https://schema.org", "@type": "Recipe", "name": "Przykład"},
  "rights_attestation": "I have the right to submit these data for my private recipe collection"
}
```

`source_url` sam w sobie nie upoważnia backendu do pobrania HTML. Statusy importerów: `link_only`, `permission_required`, `draft_requires_review`, `validated`, `blocked_by_policy`, `error`.

## Przykład swap/undo

```json
{
  "meal_slot_id": "slot-uuid",
  "new_recipe_version_id": "version-uuid",
  "variant": "in_stock",
  "expected_plan_version": 7
}
```

Odpowiedź 200 dopiero po transakcyjnym zatwierdzeniu; 409 `PLAN_VERSION_CONFLICT` ze stanem aktualnym. Undo tworzy nową wersję planu (nie cofa w czasie już spożytych produktów).

## Statusy odpowiedzi

- 401 brak sesji, 403 brak uprawnień, 404 brak zasobu lub ukrywanie cudzych zasobów, 409 konflikt, 422 walidacja / brak danych, 424 niezależne API niedostępne bez wpływu na core, 429 limit, 503 niegotowość serwisu.

## W01-A implemented contract (PR #2 merged; tests and review passed)
Auth register requires explicit subsequent login. GET /auth/session returns user, csrf_token and expires_at, never the raw session cookie. Trusted Origin and application/json for POST/PUT; authenticated mutations additionally X-CSRF-Token. Private responses no-store. Household mutations require Idempotency-Key (UUID), expected_version for target/slot updates; logout revokes and does not need an idempotency key.

GET /households returns households; POST creates owner and five real presets atomically. GET /households/{id}/members returns members; POST adds a non-login resident or guest, not account access. PUT /households/{id}/members/{member_id}/nutrition-target appends history; GET .../nutrition-target/history reads it. GET/PUT /households/{id}/meal-slot-presets returns version and slots with id/name/ordering/default_time/default_share/repeat_weekly. Unknown targets null, true zero macro accepted, kcal known must be >0. Decimal strings up to6 integer and3 fraction digits, integer JSON accepted, fractional JSON float forbidden. Source user_set; immutable history. UI must distinguish target from consumed/calculated nutrition.

Invitations and private recipe catalogue remain next slices, not implemented endpoints in A. No implicit sample goals on real signup. Household scope is always checked, including idempotency replay.

## W01-B implemented contract (PR #3 merged; tests and review passed)

All routes below require a session; mutations require trusted Origin, JSON, X-CSRF-Token and a UUID Idempotency-Key. Responses are private `no-store`. Household authorization requires an active member with `access_enabled=true`; changing access does not change resident participation or nutrition history.

| Method | Path | Input / result |
|---|---|---|
| POST | `/households/{id}/invite` | Owner only; `{role: "editor"\|"viewer", member_id: UUID\|null}`. Create a 24-hour invitation for an unlinked non-guest resident or a new resident. |
| GET | `/households/{id}/invitations` | Owner only; `{invitations: [...]}` containing metadata, never codes, hashes or nonces. |
| POST | `/households/{id}/invitations/{invitation_id}/revoke` | Owner only; `{expected_version}`. Versioned invalidation of a pending invitation. |
| POST | `/household-invitations/accept` | `{token}` in JSON only; returns `{household, member}`. Atomically links the recipient account and consumes the invitation. |
| PUT | `/households/{id}/members/{member_id}/access` | Owner only; `{expected_version, role: "editor"\|"viewer", access_enabled: boolean}`. Returns the updated member; canonical owner cannot be demoted or revoked. |

Invitation metadata: `id`, `role`, nullable `member_id`, `expires_at`, `status` (`pending`, `accepted`, `revoked`, `expired`), `version` (starts at 1). Creation adds a 64-character lowercase hexadecimal `token`; other responses omit it. Member DTO adds `access_enabled` and `access_version` (starts at 0). These access versions are independent of target versions.

Creation retries store only an invitation reference and regenerate the same code after current owner authorization. Secret rotation invalidates previous codes and regeneration. Acceptance retries reauthorize the current membership; a revoked account cannot regain access through replay. A consumed code with a new key is rejected. Code submission never appears in URLs, browser persistence or audit metadata. Invitation delivery is manual; the app sends no email.

Linking an existing resident preserves member ID, targets, exact Decimal values, nulls, zeros and all profile history. Revoking account access preserves `active=true` and those same records. Guests cannot gain login access. Viewer reads are authorized but household writes are forbidden. Recipe catalogue remains W01-C.

## W01-C implemented contract (PR #4 merged; gates passed)

These routes extend the same authenticated, private `no-store` contract. Mutations require trusted Origin, JSON, X-CSRF-Token and UUID Idempotency-Key. Access is rechecked on each request and replay. No URL import, network fetch, validation or nutrition calculation is activated by this slice.

| Method | Path | Input / result |
|---|---|---|
| GET | `/households/{id}/recipes` | `limit` 1–20 (default 20), optional UUID `after`; `{recipes: RecipeSummary[], next_cursor: UUID\|null}` ordered by recipe UUID ascending. |
| POST | `/households/{id}/recipes` | Editor/owner; RecipeInput; 201 immutable first version. |
| GET | `/households/{id}/recipes/{recipe_id}` | Current RecipeDetail; foreign household resources hidden with 404. |
| PUT | `/households/{id}/recipes/{recipe_id}` | Editor/owner; complete RecipeInput plus strict positive integer `expected_version`; append a version, 409 on conflict. |
| GET | `/households/{id}/recipes/{recipe_id}/history` | `limit` 1–5 (default 5), optional positive integer `before_version`; descending versions in `{history: RecipeDetail[], next_before_version: int\|null}`. |
| POST | `/households/demo` | Authenticated user; `{confirmation: "create_separate_demo"}`; 201 `{household}` creates a separate owned demo atomically, never alters the selected household. |

RecipeInput contains `title` (1–160 characters), `instructions` (1–30 plain text steps, each 1–500 characters), `ingredients` (1–40), and `rights_attestation: "i_am_author"`. Ingredient fields: `name` (1–160), required `amount` (null or exact positive Decimal string/JSON integer, up to 999999.999 and three fractional digits), `unit` (`g`, `ml`, `piece`, `unknown`) and `weight_state` (`raw`, `cooked`, `as_packaged`, `unknown`). Floats, booleans, exponent notation, excess precision and unknown input fields are rejected. No implicit conversion to grams. Actual UTF-8 request bodies remain limited to 16 KiB.

RecipeSummary contains `id`, `household_id`, `version`, `title`, `created_at`, `status: "draft_requires_review"`, `planner_eligible: false` and `{code,message}` warnings. RecipeDetail adds `version_id`, instructions, ingredients and the complete version snapshot. Ingredient amounts are canonical strings or null. Nutrients (`kcal`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`) remain null, ingredient nutrient provenance is null, and all allergens remain `unknown`. Yield mass, preparation/cooking time, prices, storage method and validation reference remain null. `servings: 2` in original demo recipes expresses intentional recipe design; it does not assert measured yield or per-person energy. Other recipes have unknown servings. Recipe snapshots do not supply calculated calorie totals.

Server-owned provenance distinguishes `original_fixture` text by MealForge (`CC0-1.0`, scope `original_recipe_text`) from `private_user_content` (private use, license unknown). Editing a demo recipe retains original attribution in `original_origin` and the previous immutable `source_version_id`; the new contribution does not automatically inherit CC0. User confirmation concerns their own contribution. License, origin, nutrient, safety and planner fields cannot be injected through RecipeInput.

Demo requires the audited runtime fixture and creates two resident profiles (2700/1600 kcal, every macro null), five meal slots and three draft recipes in the same transaction. Missing or changed fixture aborts with 503, without partial household creation. Household DTO adds `source: user_created|demo_seed`; target DTO adds `source: user_set|demo_seed` and demo warnings. Legacy stored responses default only to their known pre-demo source semantics, preserving idempotent replay compatibility.

## W02-A link-only contract (PR5 merged; gates passed)

Authenticated household routes retain current authorization, private `no-store` responses and existing 16 KiB request bounds. POST requires editor/owner, trusted Origin, JSON, CSRF and UUID Idempotency-Key. Viewer may read; revoked access cannot read or replay a write.

| Method | Path | Input / result |
|---|---|---|
| GET | `/households/{id}/recipe-links` | `limit` 1–20 (default 20), optional UUID `after`; `{recipe_links: RecipeLinkSummary[], next_cursor: UUID\|null}`, ascending UUID order. |
| POST | `/households/{id}/recipe-links` | LinkInput; 201 RecipeLinkDetail. A new key for the same canonical URL returns 409 `RECIPE_LINK_EXISTS`; retry with the original key returns the committed link after current authorization. |
| GET | `/households/{id}/recipe-links/{link_id}` | RecipeLinkDetail; foreign resources hidden with 404. |

LinkInput: `user_title` (1–160 characters), `source_url` (strict HTTPS URL, up to 2048 encoded UTF-8 bytes both before and after validation), optional nullable `own_note` (up to 2000 characters), and `own_contribution_attestation: "i_am_author_of_label_and_note"`. Extra fields are forbidden. The declaration covers only the user's label/note. Protected source text, images, nutrition and safety fields are not imported.

Summary: `id`, `household_id`, `user_title`, `source_url`, `host`, nullable `source_id`, `source_registry_checked_at`, `created_at`, `version: 1`, `status: "link_only"`, `planner_eligible: false`, `license: null`, `automatic_fetch_enabled: false`, `nutrition_status: "unknown"`, `allergen_status: "unknown"`. Detail additionally contains `canonical_url`, `own_note`, `own_contribution_attestation` and `actor_user_id`. Summaries omit notes. Registry date is the packaged configuration's historical check date; recognition of a domain grants no rights or network permission.

Opening URL preserves fragments, query order and encoded separators. Canonical URL removes only the fragment for deduplication after safe scheme/host/default-port normalization. Unsafe numeric/local hosts, credentials, non-443 ports, raw whitespace/control/backslashes, encoded controls, malformed percent encoding, domain-changing IDNA mappings and browser dot segments are rejected. Validation performs neither DNS nor HTTP; a syntactically allowed domain is not evidence of public resolution or permission for future fetching. No edit/delete/import endpoints exist in A. Missing or changed packaged registry aborts creation atomically with 503 `SOURCE_REGISTRY_UNAVAILABLE`.

## W02-B1 own JSON-LD preview (final acceptance in progress)

POST `/households/{id}/recipe-imports/preview`: editor/owner, session, trusted Origin, JSON and CSRF; strict `{document: string, rights_attestation: "i_am_author"}`. Document<=12288UTF8bytes; outer body<=16KiB. This is a transient read computation: no idempotency requirement/record, audit write, recipe creation or persisted source. No other import route is implemented.

200 response: title, literal ingredient texts with `amount:null/unit:unknown/weight_state:unknown`, instruction texts and section paths, unverified `recipe_yield_raw` strings, source SHA256/parser_version, fixed ignored-field names, `source_mode:user_supplied_jsonld`, `rights_mode:private_user_content`, license null, nutrition/allergens unknown, draft status, planner false and `persisted:false`. Field names from JSON-LD do not grant rights, resolve references, convert units or verify nutrition/storage. Missing/malformed/ambiguous/unsupported content returns sanitized422 `JSONLD_INVALID`; unknown input fields/author attestation422, viewer403, foreign/revoked404; no-store on all responses. Preview is not the future persisted recipe-import contract in contracts/recipe-import.schema.json; B2 will extend provenance explicitly.
