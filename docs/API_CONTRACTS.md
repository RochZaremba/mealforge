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

## W01-B contract (implementation in progress; not yet verified)

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
