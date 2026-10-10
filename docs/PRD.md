# Product Requirements Document — MealForge v2

## Użytkownicy i problem

Dom dla dwojga; osobne cele energetyczne i makro, wspólne gotowanie. Cotygodniowy stres: co gotować, ile dać komu, co kupić, które słoiki są już gotowe, czego nie wyrzucać i co się zmienia po przyjściu gości. Potrzebne jest **narzędzie operacyjne dla kuchni**, nie tylko tracker kalorii.

## Success metrics (mierzyć dopiero po wdrożeniu)

- Time to generate a feasible week P50 <30 s przy przykładowym katalogu i sprzęcie; P95 mierzony w testach, a nie deklarowany.
- Wyliczony bilans porcji: ani jedna porcja nie jest przypisana dwukrotnie w testach równoległych.
- 0 przypadków planowania wykluczonych alergenów w automatycznych testach przy znanych danych.
- 0 przypadków uznania niezweryfikowanych potraw za shelf-stable.
- Zamiana jednego posiłku + cofnięcie zajmuje maks. 2–3 działania interfejsowe.
- Działający offline odczyt ostatniego zsynchronizowanego planu, zakupów, zamrożonych porcji.
- Transparentne źródła i status danych makro/licencji w 100% przepisywanej bazy.

## Epiki

| ID | P | Funkcjonalność | Minimalne kryteria |
|---|---|---|---|
| EP01 | P0 | Household/profiles | osobne osoby, goście, uprawnienia i cele |
| EP02 | P0 | Nutrition | kcal/protein/carb/fat per person/day/meal, provenance, unknown |
| EP03 | P0 | Recipes | lokalny katalog, wyszukiwanie, edytor i link-only |
| EP04 | P0 | Weekly plan | 5 slotów, powtarzalność śniadań/kolacji, lock, swap i undo |
| EP05 | P0 | Batches | różne porcje dla 2 osób, słoiki/chłodnia/zamrażalnik |
| EP06 | P0 | Inventory | lot ledger + reservations + FEFO |
| EP07 | P0 | Shopping | agregacja, potrzeby minus zapasy, przyjęcie zakupów |
| EP08 | P0 | Events | goście, absencje, no cook, poza domem, rerouting planu |
| EP09 | P1 | Recipe import | URL z Share Target/PWA, JSON-LD na licencjonowanych źródłach, dane użytkownika, dedupe |
| EP10 | P1 | One Click Week | solver, preferencje, wielokryterialna optymalizacja |
| EP11 | P1 | Feedback | ranker bez auto-medical decisions |
| EP12 | P1 | PWA | instalacja, offline read, bezpieczna sync queue |
| EP13 | P2 | Visual wow | kitchen mode, batch planner, etykiety QR/PDF |
| EP14 | P2 | Insights | waste, ceny, różnorodność, błonnik, zakupy w historii |
| EP15 | P2 | Import scale | 100 verified local recipes, później 500+ zgodnie z prawami |

## Standardowe profile demonstracyjne

- Osoba A: 2700 kcal/dzień, B/W/T definiowane osobno przez użytkownika (bez sztywnych przykładowych g, jeśli nie podano).
- Osoba B: 1600 kcal/dzień, tak samo indywidualne makro.
- Pięć domyślnych posiłków. Śniadanie i kolacja takie same cały tydzień; możliwość indywidualnego wyjątku w środę.
- W sobotę +3 gości na obiad; w środę `no cooking`; w niedzielę batch cook z 10 słoikami, z czego 4 w zamrażarce.

## Najważniejsze reguły biznesowe

1. Recipe = szablon składników / procesu; RecipeVersion = migawka receptury; MealBatch = faktyczny uzysk; BatchPortion = realna porcja w danym pojemniku.
2. PlannedMeal odnosi się do profilu uczestników; jedna potrawa może mieć różne personalizowane `PlannedPortion` i dodatki.
3. `calories`, `protein`, `fat`, `carbs` są opcjonalne i mają provenance. Brak nie jest równoznaczny z zerem.
4. Zakupy nie mogą odjąć tego samego zapasu dwa razy ani zapasu już zarezerwowanego.
5. `No cooking` może przypisać gotową porcję albo oznaczyć jedzenie poza domem. Nie obiecuje, że kalorie posiłku poza domem są znane.
6. Zablokowany posiłek jest niemodyfikowalny dla automatycznego planera.
7. Recipe bez zweryfikowanych alergenów nie może trafić do planu osoby z odpowiadającym ograniczeniem bez świadomej decyzji.
8. Zmiana celu/makro jest wersjonowana; historycznie zjedzony posiłek zachowuje snapshot.
9. Wyjście z planu i undo muszą mieć concurrency kontrolę.
10. Reguły do przechowywania gotowych dań są osobne od zasad domowego wekowania.

## Out of scope pierwszego MVP

- Pomiar medyczny i leczenie dietą; diagnozy.
- Automatyczne zamawianie zakupów i integracje z marketami.
- Masowe scrapowanie komercyjnych serwisów z chronionymi treściami.
- Gwarantowana trwałość słoików w temperaturze pokojowej.
- Automatyczny deployment kodu proponowanego przez AI.
- Rozpoznawanie gramatury i wartości odżywczej po samym zdjęciu z gwarancją dokładności.

## Historia akceptacyjna #1

Osoba A 2700 i Osoba B 1600 jedzą tę samą partię obiadu; system rozdziela większą/mniejszą wagę i dodatki, przechowuje oba bilanse, generuje jeden przepis zbiorczy i jedną listę zakupową. Po zmianie sobotniego obiadu na 5 osób zakupy i plan są aktualizowane tylko w zakresie powiązanych produktów, można wykonać undo.

## Historia akceptacyjna #2

Wklej URL z `aniagotuje.pl` lub `kwestiasmaku.com`: system zapisuje kartę z linkiem do oryginału i pokazuje status `link_only`; użytkownik może wprowadzić własne notatki / składniki w prywatnym edytorze. Nie następuje nieautoryzowany fetch/copy fotografii lub artykułu. Na dozwolonym API lub dostarczonym JSON-LD aplikacja potrafi importować uporządkowane dane z walidacją i atrybucją.

## Historia akceptacyjna #3

Przygotuj obiad w słoikach: użytkownik widzi jednoznacznie `lodówka`, `zamrażarka` lub `zweryfikowana konserwa ciśnieniowa`. Nie pojawia się deklaracja shelf-stable dla zwykłego gotowanego chili po pasteryzacji wodnej.
