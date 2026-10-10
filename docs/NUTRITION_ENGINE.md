# Nutrition Engine — kontrakt i walidacja

## System jednostek i arytmetyka

- Storage basis: na 100 g części jadalnej (`kcal, protein_g, carb_g, fat_g, fiber_g, saturated_g, sodium_mg`).
- Internal: `Decimal` lub scaled integers, nie `float` do akumulacji i sumowania makro.
- Gramatura `IngredientAmount` ma `value`, `unit`, `raw_or_cooked`, `edible_fraction`, `confidence`, `conversion_source`.
- Obliczenie: `nutrient(recipe ingredient) = nutrient_per_100g * edible_grams / 100`; `recipe_total = sum ingredient values`; `portion = total * measured portion_mass / actual_yield_mass` przy jednorodnej partii.
- Dodatki osobno, `partially_missing=true` jeśli dowolny istotny składnik nie ma wartości. Zwracaj `known_total` + `missing_ingredient_ids`, nie udawaj kompletności.
- Wartość energii etykietowej i energia przeliczona z B/W/T mogą nie być identyczne (np. błonnik, zaokrąglenia). Nie poprawiaj jednej przez fałszywe zmiany makro.

## Dopasowanie produktów

1. Dokładne `barcode` / verified product ID.
2. Alias ingredient, lokalny zatwierdzony słownik.
3. USDA/OFF match ze zgodnym rodzajem/stanem.
4. Jeśli niepewne: `needs_confirmation`; nie automatyzuj w plannerze.

Dodatkowe wymiary: raw vs cooked, bone/skin/peel/inedible portion, salted vs unsalted, brand variations, liquid density. Brak density dla ml->g = nieznane, chyba że użytkownik poda własny współczynnik. Jednostki `łyżka`, `szklanka`, `szt.` tylko z profilem produktu, nigdy uniwersalnym założeniem 1 szt = 100 g.

## Uzysk i utrata

- Warzywa, mięso, kasze zmieniają masę podczas gotowania — kuchnia powinna móc zważyć **rzeczywisty batch yield**.
- Jeżeli znane surowe składniki i rzeczywisty końcowy uzysk, total kcal pozostaje sumą energii składników z odpowiednimi zweryfikowanymi retencjami; masa 100g potrawy przelicza się z yield. Nie stosuj 1:1 dla surowego/ugotowanego kurczaka.
- Jeśli nie ma zmierzonego uzysku, podaj ostrożny szacunek, nie precyzyjne słoiki.

## Profil celów

Kalorie i makro per osoba i dzienny/meal-slot weight. User może podać kCal i B/T/W niespójne z uproszczonym `4p + 4c + 9f`. Pokaż ostrzeżenie i umożliw świadomą zmianę; nie skoryguj celów po cichu. Plans mają soft deviations; alergia twarda.

## Alergeny

Składniki z niejasnym label lub składem przetworzonym nie mogą być traktowane jako bezpieczne dla alergika automatycznie. Data model ma `known_contains`, `known_not_contains`, `unknown`, ewentualnie cross-contact unknown. Weryfikacja źródła ma czas/wersję.

## Golden tests

1. 100 g produktu zawiera B=10g, T=5g, W=20g; 250g -> B=25g, T=12.5g, W=50g; nie wyliczaj makro przy nieznanym g.
2. Recipe 2 kg po gotowaniu z 2000 kcal: 250g -> 250 kcal, pod warunkiem że yield 2kg rzeczywisty i partia jednorodna.
3. W 400 ml mleka z gęstością 1.03 g/ml -> 412g, przy braku density -> unknown/confirmation.
4. 6 osób x różne gramatury; suma gramów porcji <= yield.
5. Brak danych białka dla 1 składnika -> protein completeness false, nie 0.
6. User-set energy 2700 i macro g o innej energii -> ostrzeżenie, bez silent change.
7. Raw/cooked 100g nie są tym samym referencyjnym punktem.
8. Zmiana późniejszego nutrient record nie zmienia snapshot już zjedzonego meal.

## Źródła

- USDA FDC: https://fdc.nal.usda.gov/api-guide/ (CC0, API key)
- Open Food Facts: https://github.com/openfoodfacts/openfoodfacts-server/blob/main/docs/api/index.md (ODbL, user-agent, rate limits)
