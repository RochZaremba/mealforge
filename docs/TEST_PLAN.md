# Strategia testów i scenariusze E2E

## Warstwy

- **Unit**: conversions, ingredient matching, macros, target consistency, price pack calculations, storage policy, optimizer hard constraints, inventory math.
- **Contract**: OpenAPI/Pydantic shape, response versioning, external source adapter results, parser schema.org.
- **Integration**: FastAPI + PostgreSQL, migration up/down, transactional rollback/locks, household authorization, idempotency.
- **E2E**: Playwright Android-sized viewport 390x844 + desktop 1440x900, keyboard accessibility, network delay, offline/cache.
- **Security**: URL SSRF, household IDOR, CSRF, untrusted HTML/XSS, rate limits, no source-fetch for prohibited domain.
- **Acceptance**: all 15 scenarios below.

## Krytyczne scenariusze

| ID | Test | Oczekiwane |
|---|---|---|
| A01 | A 2700, B 1600, 5 posiłków | plan osobny per target i porcja; żadna liczba nie jest podstawiona |
| A02 | Śniadanie i kolacja identyczne 7 dni | pinned recipe/portion untouched by lunch regen |
| A03 | 12 porcji chili, 2 osoby | suma przydziału ≤12, żadna porcja dwa razy |
| A04 | Goście +3 sobotni obiad | tylko obiad ma 5 uczestników; zakupy updated |
| A05 | No-cook środa | leftovers, external meal lub jasny brak planu, zero cooking session |
| A06 | Swap lunch → undo | kcal/makro/stock/shopping/plan version consistent; audit remains |
| A07 | Zapasy lodówki odejmowane z zakupów | dostępne niezarezerwowane ilości odjęte raz |
| A08 | Chili w zwykłym słoiku po pasteryzacji | NIE validated shelf-stable |
| A09 | Alergia or unknown allergen | planner odrzuca niepewne i znane ryzyko |
| A10 | PWA install/last plan offline | app shell + last-known read works; mutation pending clearly shown |
| A11 | Recipe link-only Ani Gotuje | zero HTTP fetch i zero skopiowanych obrazów/tekstu |
| A12 | JSON-LD source allowed vs user-provided | parsed (recipeYield/HowToStep/@graph), but draft until validated |
| A13 | 2 równoczesne consumption same portion | jedna transakcja succeeds, druga 409; brak ujemnego stock |
| A14 | Recipe missing nutrient/weight | displayed as incomplete, not precise optimizer candidate |
| A15 | SSRF localhost/private/redirect | blocked before connection, no internal HTTP requests |

## Dodatkowe testy rekomendacji

- Samo `losowo` nie podsuwa ostatniego odrzuconego dania.
- `cofnij` przy fizycznym zjedzeniu dania nie wskrzesza inventory bez ręcznej akcji korekty.
- Pomiędzy 2 profile: osoba 2700 kcal nie dostaje porcji 1600 kcal przypadkowo.
- Po zmianie `event` w toku zatwierdzania planner zwraca version conflict, a nie nieaktualny plan.
- Użytkownik może ręcznie ustalić `protein g`, `carbs g`, `fat g` i cel kaloryczny, nawet jeśli niespójny — UI ostrzega.

## Test setup / seed

- Fixture household A 2 members/5 slots; household B oddzielny tenant; 12 oryginalnych przepisów testowych ze znanymi gramaturami i jawnie testowymi danymi nutrition; inventory prawdziwe loty.
- Dla importerów używaj tylko syntetycznego / własnoręcznie napisanego JSON-LD w `fixtures/imports`; żadnych kopii cudzych chronionych przepisów.
- Sztuczna awaria OFF/USDA/MealDB nie blokuje podstawowych operacji na lokalnych recepturach.

## Gate do oznaczania funkcji jako `done`

Polecenie, exit code, liczba testów, link do logów/zrzutów dla mobile i desktop, data. Niewykonany test = `not run`, nie `passed`. WAVE-00 definiuje rzeczywiste komendy CI; dopóki nie ma implementacji, runner zestawu weryfikuje tylko dokumentację i TOML.
