# Architektura techniczna

## Modularny monolit / hexagonal boundaries

```text
                       +-----------------------------+
Desktop/browser <HTTPS> |  Next.js PWA / React        |
Mobile PWA ------------>|  offline cache, Query      |
                       +--------------+--------------+
                                      | /api/v1 (JSON, sessions)
                       +--------------v--------------+
                       | FastAPI application          |
                       | auth + household boundary   |
                       +-----+----------+------------+
                             |          |
         +-------------------+--+    +--+----------------------+
         | Domain modules       |    | External data adapters  |
         | profiles/plans/      |    | gated Recipe JSON-LD    |
         | recipes/nutrition/   |    | TheMealDB/Wikimedia     |
         | batches/inventory/  |    | USDA/OFF (conditional)  |
         | shopping/events     |    +-------------------------+
         +----------+----------+
                    |  domain tx / unit of work
          +---------v---------+      +--------------------+
          | PostgreSQL        |      | Redis/worker queue |
          | events + versions |      | async imports/jobs |
          +-------------------+      +--------------------+
```

### Dlaczego modułowy monolit?

Mało domowników, duże zależności między planem a zapasami, wymagane transakcje. Tanie wdrożenie self-host, migracje w jednym miejscu, brak distributed saga dla zakupów.

## Ownership domen

| Moduł | Komendy i odpowiedzialność |
|---|---|
| `identity` | users, sessions, households, memberships, guests |
| `nutrition` | foods, nutrient records, conversions, recipe calculation |
| `recipes` | canonical models, versions, favorites, ratings, source provenance |
| `importers` | source policy, JSON-LD parse, URL store, approve/quarantine |
| `planning` | meal slots, portions, versioned plans, constraints, optimizer |
| `batching` | cooking sessions, yields, batch portions, jar labels, storage |
| `inventory` | inventory lots, reservations, FEFO, consumptions, transactions |
| `shopping` | demand delta, packaging, prices, checkoff, stock receipt |
| `calendar` | events and attendee/meal scopes |
| `feedback` | explainable ranking weights and quality feedback |

## Reguły przepływu

- API jest właścicielem zapisów. UI nigdy nie wylicza transakcyjnych stanów magazynowych samodzielnie.
- Planner może zapytać `inventory.availableAt(date)`, ale zmiany planu / rezerwacji zatwierdza jedna transakcja w API.
- Import network adapter nie ma uprawnień do mutacji produkcyjnego katalogu. Wynik do `draft/quarantine`; oddzielne zatwierdzenie i walidacja.
- Renderowane dane z recipe import traktować jako tekst, nigdy HTML wykonywany w kliencie.
- Worker nie posiada uprawnień do obchodzenia source policy i korzysta z tego samego permission service co API.

## Deployment

- `apps/web` Next.js, `apps/api` FastAPI, `postgres`, opcjonalnie `redis/worker`.
- Docker Compose dla development i prostego self-host; reverse proxy, TLS, domena i backup.
- HTTPS i sesje `Secure`, `HttpOnly`, `SameSite`; wyłącznie trusted origins.
- Postgres prywatny, niedostępny z Internetu.
- Jeżeli hosting darmowy odcina zewnętrzne API, core planowanie nadal działa na lokalnych zweryfikowanych przepisach.

## Własności niefunkcjonalne

- Mobile-first, a11y; 300–500 przepisów bez przesadnej złożoności wyszukiwania.
- Optymalizer bounded, timeout i fallback z jawnymi kompromisami.
- Paginacja/cursor, indeksy po household_id/dacie/source_url, telemetry tylko opt-in.
- Observability: request id, correlation id across planning transactions, traces bez health secrets, metrics błędów importu i solvera.

Patrz `docs/ADR`, `docs/API_CONTRACTS.md`, `docs/DATA_MODEL.md`.
