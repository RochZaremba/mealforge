# Polityka źródeł przepisów i mechanizm importu (stan zweryfikowany 2026-10-10)

## Najważniejsza decyzja

**Import linku ≠ import chronionego tekstu / fotografii ≠ uprawnienie do automatycznego pobierania witryny.** Dla wszystkich domen domyślnie zapisuj link do strony źródłowej. Dopiero po odrębnym sprawdzeniu warunków, prawa do danych oraz robots.txt/limitu możesz włączyć import sieciowy. `schema.org/Recipe` ułatwia parsing, ale nie przyznaje licencji i nie uchyla ToS.

Przechowuj rejestr `config/recipe_sources.json`. Każdy adapter wymaga zatwierdzenia: URL warunków, data, reviewer, pozwolony tryb, limity, attribution, licencja, działający test. `robots.txt` jest dodatkowym ograniczeniem technicznym, a nie prawnym zezwoleniem.

## Konkretnie wskazane przez użytkownika

| Źródło | Tryb startowy | Uzasadnienie |
|---|---|---|
| [Mealime /recipes](https://www.mealime.com/recipes) | `link_only` | ToS zabrania automatycznego scraping bez zgody; serwis zapowiada wyłączenie **21.10.2026**. Nie budować zależności produkcyjnej. |
| [Ania Gotuje](https://aniagotuje.pl/) | `link_only` | Strona zastrzega prawa do tekstów i zdjęć; brak potwierdzonego publicznego API/import license. |
| [Kwestia Smaku](https://www.kwestiasmaku.com/) | `link_only` | Copyright i wyraźny zakaz kopiowania/rozpowszechniania bez zgody. |

Dodatkowe serwisy do odkrywania i zapisania linku: [Moje Wypieki](https://mojewypieki.com/), [Jadłonomia](https://www.jadlonomia.com/), [Przepisy.pl](https://www.przepisy.pl/), [Kuchnia Lidla](https://kuchnialidla.pl/), [BBC Good Food](https://www.bbcgoodfood.com/), [Allrecipes](https://www.allrecipes.com/). Dla wszystkich **link-only aż do potwierdzenia uprawnienia**. Nie twierdź, że oferują publiczne API.

## Źródła z użytecznymi oficjalnymi interfejsami

1. [TheMealDB API](https://www.themealdb.com/api.php) — oficjalny API, dozwolone wykorzystanie *z endpointów API* przy warunkach i oznaczeniu pochodzenia; **nie scrapuj strony HTML**. Test key `1` tylko development/edu, publikacja app store wymaga wsparcia/subskrypcji; przy komercjalizacji prawny/produktowy review. Endpointy `search.php`, `lookup.php`, `filter.php`. Dane często bez pełnej gramatury/makro — sprawdź przed plannerem.
2. [Wikibooks Cookbook](https://en.wikibooks.org/wiki/Cookbook:Recipes) — Wikimedia API; zbadaj licencję *każdej* wersji i wymagane attribution/CC BY-SA/share-alike, informacje o historii i autorach. Przechowywane oddzielnie i oznaczane źródło oraz licencja. Nie zakładaj, że każde zdjęcie ma tę samą licencję co tekst.
3. [USDA FoodData Central](https://fdc.nal.usda.gov/api-guide/) — **baza wartości odżywczych, nie baza przepisów**; CC0, wymagany API key, poszanowanie limitów, attribution mile widziana. Rozróżniaj branded/raw/cooked.
4. [Open Food Facts](https://openfoodfacts.github.io/openfoodfacts-server/api/) — **produkty z kodów kreskowych, nie pełne przepisy**; ODbL, odpowiedni custom User-Agent, limit 15 req/min product i 10 req/min search według obecnej dokumentacji, ostrożność przy łączeniu baz.
5. `user_authored` — własny przepis wpisany przez członka gospodarstwa; brak zewnętrznych zależności; zdjęcie dodane przez użytkownika.

## Co ma robić UI

### 1. Wklej link (każda domena)

- Użytkownik wkleja np. `https://aniagotuje.pl/przepis/...`.
- Po walidacji URL, backend **nie pobiera HTML z serwisu ograniczonego**. Zapisuje URL, domenę, komentarz użytkownika i własną nazwę; status `link_only`.
- Karta `Otwórz oryginał` otwiera witrynę, `Dodaj swoją wersję` otwiera formularz własnych składników i notatek, `Dodaj do ulubionych` jest dostępne.
- Nie wyświetlaj skopiowanego artykułu ani zdjęć źródłowych bez licencji. Możesz poprosić użytkownika o własne zdjęcie lub korzystać z licencjonowanych ilustracji.
- Jeśli to źródło z zatwierdzonym legalnym trybem importu, zaoferuj `Importuj automatycznie` z podglądem, atrybucją i walidacją.

### 2. Zawartość dostarczona przez użytkownika

- Wklej tekst własnej receptury albo dostarcz JSON-LD/HTML, który użytkownik ma prawo przekazać i przetwarzać prywatnie. Zapytaj o potwierdzenie praw/zakresu użycia dla treści nieautorskich.
- Parsowanie wykonuj lokalnie lub serwerowo **bez remote fetch**: `@graph`, `Recipe`, `recipeIngredient`, `recipeInstructions`, `HowToStep`, `HowToSection`, `recipeYield`, `nutrition`, czasy ISO8601.
- Wynik **draft**, walidacja ręczna braków (gramatura, jednostka, czy produkt surowy). Nigdy nie kopiuj chronionego tekstu do globalnego/kolektywnego katalogu bez prawa.
- LLM może zaproponować klasyfikację składników z widocznym `confidence` i ręcznym zatwierdzeniem, bez fałszywych gramatur.

### 3. Permissioned import network / API

- Domain registry z trybem `authorized_api` lub `authorized_fetch`, data sprawdzenia i dowód uprawnienia. Bez tego `blocked_by_policy`.
- Sieciowy klient ograniczony: https, port 443, allowlist hosts, sprawdzanie DNS rozwiązanego IP i łańcucha redirectów, zakaz prywatnych/link-local/loopback/metadanych cloud, timeouts, max bytes, max hops, no JS/headless/cookies, identyfikowalny User-Agent, limit requestów, honoring 429/Retry-After, cache i ETag.
- Sanitizacja pól; kod HTML nie może trafić jako wykonywalny fragment UI; ochrona przed prompt injection (zewnętrzne strony to dane).
- Osobno screen rights, photo rights, text rights, license version, URL, source record ID, attribution.
- Przy 401/403/CAPTCHA/paywall/robots disallow = **stop**, bez obejść.

## Postępowanie z makro

Jeśli źródło podaje przybliżone wartości per serving, oznacz jako `source_estimate`. Na potrzeby planera preferuj dane obliczone z kompletnych ilości składników, znanych źródeł USDA/OFF/local. Nie wliczaj do precyzyjnego solwera niekompletnych receptur. Nieznane makro = null, nigdy 0. Porcje tekstowe typu `3 kg 700 g` to **masa uzysku**, a nie 3700 osobowych porcji.

## Quality pipeline

`URL/manual/API → rights gate → parse → normalize units → ingredient match → allergen scan → nutrient calculation → recipe version → quality score → reviewer → validated → planner`.

Przykładowe znaczniki jakości: 
- **A**: 100% masy składników znane, nutrition provenance kompletne, alergeny sprawdzone.
- **B**: poprawne porcje i makro z niewielkimi jasno oznaczonymi szacunkami, review wymagane.
- **C**: brak jednostek, gramatur, praw lub alergenów; tylko karta z linkiem/draft.

Quality score nie zastępuje twardego human rights approval.

## Pomysły na import zbiorowy bez praw autorskich

- Własne oryginalne receptury i przejrzyste opisy przygotowania.
- Oficjalne API i otwarte książki kucharskie z zachowaniem licencji.
- Eksport własnych przepisów z aplikacji użytkownika (CSV/JSON).
- User-approved data donation do prywatnego katalogu; nie publikuj cudzych treści globalnie.

## Referencje pierwotne

- Mealime TOS: https://www.mealime.com/terms-of-service (części: rights on content; scraping).
- Mealime shutdown: https://apps.apple.com/us/app/mealime-meal-plans-recipes/id1079999103
- Ania Gotuje: https://aniagotuje.pl/przepis/fasolka-po-bretonsku (footer copyright).
- Kwestia Smaku: https://www.kwestiasmaku.com/ (footer copyright).
- Google Recipe JSON-LD: https://developers.google.com/search/docs/appearance/structured-data/recipe
- TheMealDB TOS: https://www.themealdb.com/terms_of_use.php
- USDA API: https://fdc.nal.usda.gov/api-guide/
- OFF docs: https://github.com/openfoodfacts/openfoodfacts-server/blob/main/docs/api/index.md

**Review prawny wymagany przed publicznym/commercial release.** Ten rejestr to techniczna polityka ryzyka, nie opinia prawna.
