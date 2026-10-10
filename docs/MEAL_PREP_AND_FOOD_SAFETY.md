# Meal Prep, słoiki i bezpieczeństwo żywności

## Cel

Użytkownicy gotują raz lub dwa razy w tygodniu, wkładają jedzenie do pojemników/słoików i chcą na cały tydzień zapasów. System powinien automatycznie podpowiadać, które porcje do lodówki, które do zamrażarki, a kiedy rozmrozić. **Słoik nie jest automatycznie wekiem trwałym poza lodówką.**

## Klasy przechowywania

| tryb | opis | domyślne warunki |
|---|---|---|
| `refrigerated_ready_meal` | gotowa potrawa w czystym pojemniku/słoiku, chłodzenie | wiele gotowanych resztek maks. 3–4 dni w prawidłowej lodówce wg USDA; do odmiany potraw mogą być inne zasady |
| `frozen_ready_meal` | porcja w odpowiednim pojemniku, zamrożona po schłodzeniu | daty jakości zależą od potrawy; nie stwierdzaj, że długie mrożenie samo zmienia jedzenie w shelf-stable |
| `verified_canned_food` | konserwacja wg zweryfikowanej receptury/procesu | tylko dla dokładnie przypisanej, zweryfikowanej procedury i sprzętu; po zmianie składników proces może nie być ważny |

## Reguła fail-closed

Żaden przepis importowany z blogu lub modelu AI nie może otrzymać flagi `verified_canned_food` tylko dlatego, że nazwa/tekst zawiera `wekowanie`, `pasteryzacja`, `słoiki`, `próżnia`. Tak samo zamknięta zakrętka nie jest dowodem skutecznej konserwacji. Niskokwasowe potrawy, mięso, strączki, sosy itp. nie mogą być traktowane jako bezpieczne do trwałego przechowywania w temperaturze pokojowej po zwykłej kąpieli wodnej.

Każdy `verified_canned_food` wymaga:

- source URL do procedury przebadanej przez instytucję wskazaną w allowlist, np. [NCHFP](https://nchfp.uga.edu/),
- potwierdzenia zgodności składu, proporcji, wielkości słoika, wyposażenia i warunków,
- jawnie udokumentowanej procedury *ze źródła*, bez generowania czasu/ciśnienia przez LLM,
- dowodu review i wersji procedury,
- ponownej walidacji po zmianie receptury.

Jeśli brak dowolnego wymagania, pokaż `Brak potwierdzonej metody bezpiecznego wekowania — przechowuj w lodówce lub zamroź zgodnie z zasadami.`

## Planowanie partii

1. Użytkownik wybiera 2–4 dania i planuje sesję w niedzielę.
2. Aplikacja agreguje składniki i posiłki, dopasowuje sprzęt, nadaje kolejność kroków i wylicza **planowaną** liczbę porcji.
3. Po gotowaniu użytkownik podaje **zważony końcowy uzysk** i liczbę pojemników.
4. Algorytm porcjuje według celów użytkowników, rozmiarów pojemników, rezerwuje konkretne słoiki i tworzy etykiety.
5. Porcje na dalsze dni są domyślnie kierowane do zamrażarki, jeśli przekraczałyby ostrożny czas chłodniczy.
6. Zmiany statusu i miejsca są zdarzeniami magazynowymi. Przestawienie słoika do zamrażarki nie zmienia gramów ani makro.
7. Oznaczenie `consumed` zużywa fizyczny BatchPortion i realizuje zaplanowany posiłek; nie może dokonać tego drugi użytkownik.

## UI / etykiety

Etykieta: nazwa, batch ID/QR, data, masa netto, zawartość i alergeny (jeśli znane), miejsce przechowywania, zalecany termin, czy wartości makro są pełne, dedykowany członek lub `wspólna`. Nie drukuj precyzyjnej daty shelf-stable dla custom potrawy bez zatwierdzonej procedury.

## Testy blokujące

- Mięsne chili zamknięte w słoiku i potraktowane gorącą wodą nie uzyskuje `verified_canned_food`.
- Receptura z nieznaną licencją/nieznanym składem nie dostaje automatycznie procedury konserwacji.
- Potrawa po 6 dniach przechowywania w lodówce (typowy cooked leftover) nie jest automatycznie uznana za bezpieczną.
- 500 ml słoik nie jest automatycznie równoważny 500 g posiłku.
- Nie planuj tej samej porcji dla dwóch osób/dni; test współbieżności.

## Wiarygodne źródła

- USDA FSIS leftovers: https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/leftovers-and-food-safety
- USDA food safety basics: https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/steps-keep-food-safe
- NCHFP: https://nchfp.uga.edu/ (zweryfikowane procedury)
- NCHFP low-acid safety: https://nchfp.uga.edu/newsflash/using-broth-when-canning

To dokument projektowy, nie substytut instrukcji bezpieczeństwa dla konkretnego produktu.
