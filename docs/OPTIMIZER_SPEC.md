# Optymalizacja planu tygodnia — model implementacyjny

## Indeksy

- `d ∈ days`, `m ∈ slots` (5 domyślnie), `p ∈ persons`, `r ∈ recipe_versions`, `b ∈ batches`, `i ∈ ingredients`.
- `x[d,m,r] ∈ {0,1}` wybór wspólnego przepisu; `s[d,m,p,r] ∈ Z+` porcja w kwantach 10g lub przyjmuje inną granulację z kontroli dokładności.
- `y[r,cooking_session] ∈ {0,1}` batch; `z[lot,i,day]` pobranie z magazynu; wydarzenia zmieniają zbiory uczestników.

## Hard constraints

- Dla osoby z alergią/usuniętym składnikiem recipe candidate jest zabronione; gdy allergen data unknown -> wykluczenie lub ręczna weryfikacja poza auto mode.
- Recipe meal type i ulubione locked meals respektowane.
- Suma wykorzystanych porcji z batch nie przewyższa dostępnych, zamrożonych/wygaśniętych porcji nie używaj, jeśli wymagają odmrożenia w nierealnym czasie.
- Liczba porcji na posiłek odpowiada wydarzeniu, wszelkie osoby z eventu `absent` nie dostają posiłku.
- Stan magazynu nie może spaść poniżej 0; uzależnienia od kupna produktów wyrażone jawnie w shopping needs.
- Storage window: bez planowania spożycia zwykłych cooked leftovers po datach bezpiecznych dla wybranego trybu.
- `locked` i `repeat_rule` dot. śniadań/kolacji pozostają takie same poza wyjątkami.
- `unknown nutrient` eliminuje recipe z precyzyjnej auto-optymalizacji; manual draft jest dozwolony z oznaczeniem niepewności.

## Soft objective — wagi konfigurowalne

`minimize( w_kcal * abs(kcal-plan_target) + w_macro * macro_deviation + w_money * shopping_spend + w_time * cooking_minutes + w_sessions * distinct_sessions + w_waste * expiring_food + w_repeat * unwanted_repeats + w_preference * dislike_score )`

Wagi muszą być czytelne i testowane przeciwko ekstremom (np. wagi ceny nigdy nie mogą przebić alergenu). Tolerancje docelowe: kcal ±5%, makro ±10% jako cele, nie gwarancje; wymagana raportowalna `infeasible`/`best_effort`.

## Porcje

Wspólna baza potrawy + osobne dodatki (ryż, pieczywo, warzywa, sos) per osoba. Scaling przez masę wyniku rzeczywiście ugotowanego, a nie tylko objętość naczynia. Podsumowanie tygodnia dla osób *osobno*, plus sumy shopping/batch *wspólne*.

## Algorytm / implementacja

1. Generate candidate recipes (validated + restrictions/availability).
2. Pre-calc portion nutrient vectors from complete verified ingredients.
3. Prioritize locked/repeated and existing batches.
4. Solve bounded (np. initial 10–20 s config) CP-SAT over selected candidates, capped memory.
5. Przy timeout -> valid best-feasible or deterministic heuristic; never bypass hard constraints.
6. Explain infeasible: `Insufficient complete recipes`, `Storage limits`, `Allergen exclusions`, `Too few options`, `Cannot meet targets`.
7. `seed` i snapshot input zapisane w plan versions; swap uses same filters, preserves affected plan segments and emits diff.

## Tests

- Dwie osoby 2700/1600 kcal, ten sam przepis z innymi porcjami.
- Powtarzanie śniadania/kolacji przez 7 dni, pinned meal unaffected.
- Event +3 only Saturday lunch, no cook Wednesday.
- 8 porcji batch na 9 żądań -> error/extra batch, nie 9th phantom portion.
- Allergic ingredient in only option -> infeasible, nie naruszaj constraint.
- Underconstrained weekly target -> explain non-perfect, nie invent macro.
- Same seed/data -> same plan ID-independent meal selection.
- Swap + undo = same business state except immutable audit history.
