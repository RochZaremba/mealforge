# UX/UI — design system i ścieżki użytkownika

## Główna zasada

**Trzy najczęstsze czynności w maksymalnie 1–3 akcjach:** zobacz co dziś jemy, zamień danie, odhacz zakupy/wyjmij gotową porcję. Nie buduj konfiguratora typu ERP.

## IA

Mobile bottom tabs: `Dzisiaj`, `Plan`, `Przepisy`, `Kuchnia`, `Zakupy` (magazyn pod Kuchnia). Desktop sidebar + większy kalendarz. Osobne ekrany: `Gospodarstwo`, `Cele`, `Powiadomienia`, `Źródła`, `Ustawienia`.

### Dzisiaj

Nagłówek: dzień + szybka liczba aktywnych osób, 5 kart posiłków w kolejności, status `do zrobienia / gotowe w lodówce / rozmrozić / jedzone poza domem`. Dla każdej karty: danie, osoby, ich porcje, makro na osobę, `Zamień`, `Zjedzone`, `Przygotuj`, `Zamień na porcję z zapasów`. U góry paski plan vs realizacja **osobno per osoba** (przełącznik profilu).

### Plan tygodnia

Mobile: dzień swipe lub kalendarz 7 dni w pionie; desktop: 7 kolumn, 5 wierszy. Potrafi: repeat śniadań/kolacji, lock, swap undo, wydarzenia, szybka zmiana grama/uczestnika, analiza delta makro. `One Click Week`: wybierz cele i ograniczenia, preview, feasibility, commit.

### Przepisy

Na telefonie oferuj `Udostępnij do MealForge` przez PWA Web Share Target, jeżeli platforma wspiera tę funkcję, a w innych przypadkach prosty paste URL. Linki z niezatwierdzonych źródeł nigdy nie triggerują ukrytego fetcha.

Filtry: rodzaj posiłku, czas, kuchnia, makro, białko, meal-prep, freezable, przechowywanie, koszt jeśli znany, `co mam w lodówce`, alergen, ocena. Karty: miniatura tylko licencjonowana lub neutralny placeholder, źródło, quality score, `Importuj URL`. Oddziel widok `Zapisane linki` z badge `Wymaga ręcznej receptury`.

### Kuchnia / Meal Prep Studio

`Planuj sesję` → powiąż przepisy → checklista sprzętu i składników → krok po kroku z timerami → `Zważ gotowy batch` → podziel per osoby → `Wybierz lodówka/zamrażarka` → drukuj naklejki. Słoiki wizualizowane przez kafelki, nie obiecuj shelf-stable. `Magazyn` = lodówka/zamrażarka/spiżarnia z ilościami i FEFO.

### Zakupy

Kategoria sklepu / produkt / łączna ilość / w jakim daniu / do kupienia / kupione. Wspólne odhaczanie z aktualizacją sync. Po zakończeniu `Dodaj do zapasów` (potwierdzenie zakupionej ilości, data i lokalizacja).

### Wydarzenia

FAB `+ wydarzenie`: `Nie gotujemy`, `Nie ma mnie na posiłku`, `Goście`, `Jedzenie poza domem`, `Gotowanie na zapas`, `Wyjazd`. Wpisanie zakresu, meal slot, uczestników, liczby gości. `Zobacz wpływ na plan i zakupy` diff, po akceptacji commit+undo.

### Profile

Wybierz osobę → cel (redukcja/rekompozycja/utrzymanie/masa/custom) → kalorie, B/T/W *w gramach*, podział na 5 posiłków, alergie/wykluczenia → przegląd i świadome zatwierdzenie. Nie defaultuj profilu zdrowotnego na podstawie pamięci użytkownika.

## Język produktu

Przyjazne, konkretne nazwy: `Zaplanuj tydzień`, `Zamień`, `Cofnij`, `Danie z lodówki`, `Przygotuj 8 porcji`, `Zważ gotowe`, `Przenieś do zamrażarki`. Nie pokazuj technicznych błędów Pydantic. Braki danych: `Brakuje gramatury 2 składników — nie możemy policzyć makro`.

## Accessibility/performance

- Cel WCAG 2.2 AA, klawiatura i focus, aria labels, alternatywa dla drag/drop, kontrast >= wymaganiom WCAG, duże touch targets ok. 44px.
- Loading state i optimistic updates wyłącznie z możliwością rollback. Toast `Zapisano` tylko po API confirmation; offline `Oczekuje na synchronizację`.
- Szybkość: cache ostatniego tygodnia i najczęstszych przepisów, debounce search, server rendering tam gdzie korzystne; metryki mierz realnie.
- Design: ciepłe neutralne barwy, czytelne fotografie tylko za zgodą/licencją, hero nie kosztem ergonomii; bright/dark, reduced motion.

## E2E click-path target

1. Tworzenie domu + drugiej osoby: jeden kreator.
2. Zmiana sobotniego obiadu na inny: karta → `Zamień` → wybór; `Cofnij` bez szukania historii.
3. Trzech gości na sobotę: FAB → `Goście` → `3` + `obiad` → `Zastosuj`.
4. Posiłek w pojemniku: Kuchnia → `Zjedzone` z możliwością odwrócenia w bezpiecznym zakresie.
5. Import z Ani Gotuje: Przepisy → `+ URL` → karta z linkiem → `Dodaj własną wersję` bez automatycznego naruszenia praw.
