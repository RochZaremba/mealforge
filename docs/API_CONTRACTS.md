# API v1 — kontrakty use-case

**Prefiks:** `/api/v1`. JSON; auth przez bezpieczne cookies lub sesję z CSRF policy. W odpowiedziach `problem+json` z `error_code`, `message`, `request_id`, `field_errors` (opcjonalnie). API generuje docelowy OpenAPI z kodu FastAPI. `contracts/openapi.yaml` to projekt startowy — w WAVE-00 zastąpić zsynchronizowaną specyfikacją.

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
