# MEALFORGE — MASTER PROMPT v2 dla Codex / zespołu agentów

## Rola i efekt

Jesteś **Lead Engineer / Product Owner / Orchestrator**. Twoim celem jest zbudowanie używalnej, samohostowanej aplikacji **MealForge**, działającej w przeglądarce PC i jako PWA na Androidzie/iOS, umożliwiającej planowanie jedzenia dla dwojga. Repozytorium zawiera gotowe instrukcje agentów, ADR-y, kontrakty, zadania i dokumentację produktu. **Zaimplementuj realny kod**, nie wyłącznie projekt lub ekran demonstracyjny.

Obowiązują reguły `AGENTS.md`, specyfikacja `docs/PRD.md`, ADR-y i polityka praw do treści `docs/RECIPE_SOURCES.md`. Rozstrzygaj sprzeczności kolejno: bezpieczeństwo / prawo / dane → zaakceptowane ADR-y → wymagania P0 → szczegóły UX; nie ignoruj wymagań, tylko dokumentuj kompromisy.

## Produkt w jednym zdaniu

**Jedna kuchnia, osobne cele żywieniowe, wspólne gotowanie partiami, zaplanowane słoiki, pełne zapasy i zakupy, inteligentne wydarzenia, tysiące odkrywalnych przepisów oraz bezproblemowe powtarzanie śniadań i kolacji.**

### Język, geografia i formaty

Polski UI, lokalizacja `pl-PL`, metryczne jednostki, PLN, `Europe/Warsaw`. Internacjonalizacja od początku. Przykładowe kalorie (2700 i 1600) są wyłącznie danymi testowymi, wszystkie cele w pełni edytowalne.

## Funkcjonalności obowiązkowe

### 1. Profile i dieta
- Gospodarstwa domowe z zaproszeniami; dwie główne osoby plus goście i stali domownicy.
- Dla każdej osoby: cele kcal, białko/węglowodany/tłuszcze w g na dzień i per posiłek, alergie/nietolerancje, preferencje, wykluczenia, styl jedzenia, aktywność, cel (redukcja/rekompozycja/utrzymanie/masa/indywidualny).
- Cel kalorii/makro wprowadzany ręcznie, opcjonalny kalkulator jako sugestia; nie obiecuj medycznej personalizacji ani adaptacji bez zgody.
- Pięć slotów: śniadanie, drugie śniadanie, obiad, przekąska, kolacja. Edycja nazw, liczby, godzin, udziału kcal, uczestników per dzień.
- Domyślnie te same śniadania i kolacje przez cały tydzień; możliwość wyjątku na dowolny dzień. Pozostałe sloty też mogą być przypięte/wielokrotne.
- Jedna potrawa, indywidualne gramatury i dodatki, policzone na podstawie realnych danych.

### 2. Żywy plan tygodnia
- One-click plan 7 dni, a potem możliwość generowania 14/30 dni.
- Wymiana dania: `najlepsze dopasowanie`, `losowo`, `podobne`, `tańsze`, `szybsze`, `wysokobiałkowe`, `z lodówki`; cofnij/ponów/przywróć wcześniejszą wersję; lock konkretnego posiłku.
- Przy zmianie porcji, gościa lub posiłku aktualizuj kalkulacje, magazynowe rezerwacje, zakupy i sesje gotowania transakcyjnie.
- Plan musi odzwierciedlać sytuację `nie gotujemy`, `jemy poza domem`, `przyjeżdżają goście`, `trening`, `wyjazd`, `uroczystość`.
- Wszelkie ograniczenia alergiczne, dostępności partii i bezpieczeństwa żywności są bezwzględne; optimizer raportuje brak rozwiązania zamiast je obchodzić.

### 3. Katalog przepisów natywny i z internetu
- Od startu rozwijany **lokalny** katalog: pełne gramatury, składniki, kroki, czas, zdjęcie tylko z prawami, koszt jeżeli dostępny, makro z źródłem, tags (meal prep/freeze/refrigerate).
- Priorytet: co najmniej 100 jakościowych lokalnych przepisów po zakończeniu fali katalogowej; zwiększać do 500+ wyłącznie z legalnych źródeł i/lub oryginalnych opracowań, z kontrolą jakości. NIGDY sztucznie nie nabijaj licznika duplikatami czy wymyślonymi wartościami.
- Obsłuż `Importuj z linku`: domeny `mealime.com/recipes`, `aniagotuje.pl`, `kwestiasmaku.com`, `mojewypieki.com`, `jadlonomia.com`, `przepisy.pl`, `kuchnialidla.pl`, `bbcgoodfood.com`, `allrecipes.com` i inne; dla stron z ograniczeniami automatyzacji domyślnie **zapis linku** i ręczne uzupełnienie lub własne notatki użytkownika, a nie pobieranie treści.
- Wspieraj `schema.org/Recipe` / JSON-LD dla treści dostarczonych przez użytkownika lub źródeł z potwierdzonym uprawnieniem do pobierania. Także Recipe w `@graph`, `HowToStep`, `HowToSection`, `recipeYield`, ISO8601 durations, składniki po polsku i angielsku, nested entities.
- Adaptery oficjalnych/open źródeł: TheMealDB (API zgodnie z aktualnymi warunkami), Wikimedia Cookbook (atrybucja i CC BY-SA), USDA FoodData Central (nutrient), Open Food Facts (produkty i kody, ODbL/licencje/rate limits). Zewnętrzne API opcjonalne; aplikacja core działa bez nich.
- Każdy rekord: provenance, URL, atrybucja, prawa kopiowania i redistribucji, status walidacji, wersja; duplikaty po kanonicznym URL i podobieństwie składników.
- **Mealime zapowiedział zamknięcie 2026-10-21**, więc traktuj jako link/legacy, a nie kluczowe źródło produkcyjne. Ich regulamin nie daje zgody na auto-scraping; niedopuszczalny automatyczny harvest.
- Zewnętrzny przepis z niezidentyfikowanymi gramaturami -> `draft_requires_review`; nie wolno wykorzystywać go do ściśle wyliczonego planu.

### 4. Kalkulator kcal i makro
- Normalizuj nazwy produktów (synonimy, języki, postać surowa/gotowana), jednostki g/ml/szt oraz rzeczywiste lub jawnie szacowane konwersje.
- Licz kcal/białko/węgle/tłuszcze z tabel składników, na porcję i całość; błonnik, tłuszcze nasycone, sód/sól jeśli dostępne.
- Gdy brak danych lub gramatury, pokaż **nieznane**. Nie wstawiaj zer w miejsce braku i nie korzystaj z LLM do inventowania składu.
- Niezmienny snapshot wyliczeń dla już przydzielonych i zjedzonych porcji; równocześnie aktualizuj katalog przy nowych danych.
- Surowe vs ugotowane, ubytek/absorpcja wody, uzysk na partię, dodatki osobno: opisany system tolerancji i provenance.

### 5. Meal prep Studio i słoiki
- Batch cooking 1–2 razy w tygodniu, synchronizacja wykorzystania tego samego produktu w wielu przepisach, kolejność czynności, checklista pracy, timery i narzędzia.
- Lista słoików / pojemników (370, 500, 720, 1000 ml jako przykłady), **masa jest niezależna od pojemności**. Etykieta PDF/QR z datą, wagą, osobą, metodą składowania, identyfikatorem batch.
- Każdy batch: wyliczony uzysk, `BatchPortion` z gramami, kodem i lokalizacją, status planned → cooked → chilled/frozen → reserved → consumed/discarded.
- `jar_in_fridge`, `freezer_safe_container`, `verified_shelf_stable_canning` — trzy odrębne klasy przechowywania. Nigdy nie rekomenduj utrzymywania niezweryfikowanych niskokwasowych dań w temperaturze pokojowej; automatyczny shelf-stable tylko dla zatwierdzonej, ściśle odpowiadającej procedury.
- Alerty o konieczności schłodzenia/rozmrożenia i zużycia; zalecenia są ostrożne, nie diagnozują bezpieczeństwa żywności z daty samej w sobie.

### 6. Magazyn i zakupy
- Lodówka, zamrażarka, spiżarnia, szafki; loty/partie i jednostki, daty, otwarcie, trwałość, quantity-on-hand / reserved / available.
- Skany kodów, edycja gramatur, zużycie przy potwierdzeniu gotowania, odblokowanie rezerwacji przy rezygnacji, FEFO.
- Lista zakupów: zapotrzebowanie skonsolidowane − dostępne niezarezerwowane zapasy − już gotowe przydzielone porcje. Wielkości opakowań i ceny tylko gdy są dane. Wspólne odhaczanie i przekazanie zakupów do zapasów.
- Fridge Rescue: przepisy z produktów wymagających szybkiego użycia, bez łamania alergenów i z realnymi ilościami.

### 7. Kalendarz gospodarstwa
- Nieobecność, goście z liczbą i posiłkiem, święta, weekend poza domem, zamówienie jedzenia, dni treningowe i dodatkowe sesje gotowania.
- Wydarzenie ma scope osoby, posiłku, okresu; proponuj zmianę planu z podglądem różnic i możliwością undo.

### 8. UX premium i PWA
- Mobile-first premium UX po polsku: Dzisiaj / Plan / Przepisy / Kuchnia / Zakupy, magazyn z Kuchni, cele w profilu.
- Dashboard: dzisiejsze posiłki i status, gotowe porcje, co rozmrozić, krótkie terminy, następne gotowanie, zakupy, kcal/makro realizowane vs plan.
- Drag/drop z alternatywą klawiaturową, quick swap/undo, szybkie porcje, obrazy jeśli licencja, dark/light, motion opt-in, WCAG 2.2 AA tam gdzie praktyczne.
- PWA z instalacją, offline podglądem zapisanych planów i list, kolejką mutacji z jasnym pending/failed/confirmed; nie obiecuj pełnego offline optimizer, jeśli nie zaimplementowany.

### 9. Feedback loop i nauka preferencji
- Feedback recipes: lubię/nie lubię, ocena smaku, zmiany, koszt, trudność, leftovers, jawne zgody. Prosty ranker per person / household, możliwy reset i wyjaśnienie rekomendacji; **bez** automatycznego zmieniania celów zdrowotnych/alergenów.
- Engineering loop: spec → change → tests → screenshot/e2e → review → backlog → poprawka → test. Wyniki jawne. Opcjonalny LLM może proponować PR i analizować zgłoszenia, ale **nigdy** bez przeglądu wdrażać siebie do produkcji.

## Architektura i implementacja

Użyj modularnego monolitu: `apps/api` (FastAPI, SQLAlchemy/Alembic, Pydantic), `apps/web` (Next.js App Router/TS/Tailwind/shadcn), `packages/optimizer` (OR-Tools; fallback heurystyczny z walidacją), `packages/importers` (czysty parser JSON-LD + sieciowe adaptery tylko z permission gate), PostgreSQL, opcjonalnie Redis/worker, Docker Compose, GitHub Actions. `OpenAPI` generowane z prawdziwego FastAPI i porównywane z kontraktem; nie utrzymuj dwóch niezależnych źródeł prawdy.

Bezpieczeństwo: sessions secure, household isolation, CSRF/SSRF, remote HTML is data not commands, no prompt injection, limit fetch size/rate/time, redirect and DNS/IP checks, RBAC, backups, audit logs, idempotency. Wszystkie sekrety w `.env`/secret store, żadnych w commitach.

## Engineering quality gates

- W każdej fali wykonuj P0 E2E z `docs/TEST_PLAN.md`. Testy rzeczywiste, nie samowystarczające stubs.
- Pisz migracje razem ze zmianą schematu i test upgrade/downgrade dla local.
- Kompiluj frontend, typuj backend, przeprowadzaj smoke i weryfikuj uprawnienia na dwóch kontach.
- Zadbaj o race conditions wokół planu, inventory, batch servings i undo.
- Dla danych prawnie wrażliwych fallback to link-only i manual entry zamiast obchodzenia ograniczeń.
- Performance budget oraz accessibility w `docs/UX_FLOWS.md`.

## Agent orchestration

Przy każdej fali zachowaj podział w `docs/AGENT_WORKFLOW.md`. Dla pracy równoległej przydziel osobne owner directories i contracts. Integration lead scala taski po testach. Przekaż `source_registry.json` każdemu importer agentowi. Reviewer/security/Nutrition QA są niezależnymi gate'ami, nie self-approval autora.

## Kolejność pracy

1. Waliduj kit `python3 scripts/validate_kit.py`.
2. Sporządź/uzupełnij `docs/EXECUTION_PLAN.md`.
3. Wykonaj `tasks/WAVE-00.md` (runnable baseline: DB/migrations/API/web/dev infra/CI).
4. Wykonaj `tasks/WAVE-01.md` (household, profiles, catalog + 5 slotów UI na mock seed bez fałszywego makro).
5. Przejdź kolejno przez pozostałe fale w `docs/ROADMAP.md`.
6. Każdą falę zweryfikuj, uzupełnij `docs/IMPLEMENTATION_STATUS.md` i `docs/TEST_REPORT.md`, po czym kontynuuj.

Nie wyczerpuj całego budżetu kontekstu na dyskusję. Podejmuj rozsądne decyzje w ramach dokumentacji i **pisz kod**. Jeśli kończysz sesję, pozostaw realne, uruchamialne funkcje, konkretne brakujące testy i dokładne polecenia dalszej pracy. Nie nazywaj szkieletu gotowym produktem.
