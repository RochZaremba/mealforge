# Feedback loop: produkt i agent engineering

## Dwa niezależne systemy

### A. Personalizacja żywieniowa

Użytkownik świadomie opt-in na przechowywanie ocen, powtórzeń i powodów swap. Ranker per osoba oraz household aktualizuje wagi: smak, czas, cena, preferowany protein, unikanie marnowania. Każda sugestia ma `why_this_recipe` i `data_sources`. Możliwość resetu i opt-out. Zmiana wag **nigdy** nie modyfikuje bezpieczeństwa, makro z katalogu ani alergii.

### B. Engineering QA

`backlog → hypothesis → patch → unit → integration → E2E → screenshot → independent review → merge → metrics → next issue`.

- Automatyczne statyczne testy i lokalne profile/reports.
- Telemetria zachowań tylko z opt-in, pseudonimizowana, bez health data w logach i promptach.
- Błędy zgłasza UI; automatyczna deduplikacja/klasyfikacja nie otwiera PR bez kontekstu i bez review.
- AI może generować patch/PR w kontrolowanym branch; nie może samodzielnie merge/deploy w produkcji ani zmieniać polityk legal/food safety.
- W review zapisz `expected`, `observed`, `test proof`, `risk`, `decision`, `owner`, `timestamp`.

## Przykładowy feedback od użytkownika

`Nie lubię tego kurczaka` → negatywny ranking dla recipe/mode, ale jeśli brak innego zgodnego przepisu solver pokazuje brak opcji, nie obchodzi alergenu. `Za dużo jedzenia w lodówce` → mniejszy batch plan / więcej FEFO. `Obiad trwał 90min, nie 30` → skorygowany household-prep-time prior, nie fałszuj globalnych danych.

## KPI

Realne: udział zamian, liczba odrzuconych propozycji, czas planowania, waste kg, planed-vs-consumed, liczba posiłków z niepełnym makro, exceptions per week, liczba błędów synchronizacji. Nie generuj marketingowych wyników z powietrza.
