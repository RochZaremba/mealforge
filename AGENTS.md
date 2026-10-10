# AGENTS.md — wiążące instrukcje repozytorium

## Misja

Budujesz **MealForge**, prywatny, mobilny i desktopowy system żywienia dwóch osób, gości i wspólnej kuchni. Autorytatywna specyfikacja: `MASTER_PROMPT.md`, `docs/PRD.md` i ADR-y. Repozytorium startuje jako SPEC KIT — nie zgłaszaj, że aplikacja jest gotowa.

## Obowiązkowy bootstrap

1. Przeczytaj `MASTER_PROMPT.md`, `docs/ROADMAP.md`, `docs/AGENT_WORKFLOW.md`, `docs/RECIPE_SOURCES.md`, `docs/MEAL_PREP_AND_FOOD_SAFETY.md`.
2. Uruchom `python3 scripts/validate_kit.py` zanim zmienisz kontrakty.
3. Sprawdź status implementacji w `docs/IMPLEMENTATION_STATUS.md` (utwórz przy pierwszej fali).
4. Wybierz najmniejszy zależny, testowalny slice z `tasks/`. Nie rozrzucaj niezakończonych funkcji po całym repo.
5. Jeśli subagents są dostępne, deleguj niezależne zakresy do `.codex/agents/*.toml`. Owner zmian i integracji to agent główny; nie pozwalaj na równoczesne edycje tych samych plików.

## Priorytety P0 — nigdy nie łam

- Jedna wspólna potrawa, **porcje per osoba** z indywidualną kalorycznością i makro; 5 posiłków domyślnie, edytowalne.
- Alergie, zakazy oraz bezpieczeństwo przechowywania to twarde ograniczenia. Nigdy ich nie rozluźniaj, żeby 'dopasować' plan.
- Energia i makro wyłącznie z identyfikowalnych danych składników; `unknown != 0`; brak wymyślonych etykiet, cen, gramatur, porcji, terminów i licencji.
- Zmiany planu, zakupów, rezerwacji i stanów magazynowych są transakcyjne i audytowalne. Zapewnij idempotencję i undo/redo z wersjami.
- Względem stron zewnętrznych: sprawdź warunki użycia **przed** aktywacją fetchu; domyślnie `link_only`, deny-by-default dla automatycznych pobrań. Nigdy nie omijaj blokad, paywalli, logowania, CAPTCHA ani rate limitów. Nie reprodukuj chronionych opisów/fotografii bez praw.
- Niskokwasowe potrawy w słoikach nie są shelf-stable po zwykłej pasteryzacji; tryb przechowywania wymaga jawnego rozróżnienia.
- Dane o zdrowiu, alergiach i wadze są prywatne; egzekwuj household authorization per endpoint. Nie wysyłaj ich do AI bez zgody.
- **Nigdy automatycznie nie deployuj na produkcję**; AI może generować PR/patch, użytkownik zatwierdza zmiany. Żadnych ukrytych telemetrycznych wycieków.

## Architektura i zakres

- Modularny monolit: FastAPI + Pydantic v2 + SQLAlchemy + Alembic + PostgreSQL, opcjonalny Redis / jobs, Next.js + TypeScript + PWA, OR-Tools dopiero dla wymagającego planowania.
- Zachowaj granice domen: identity/households, recipes/import, nutrition, planning, batches, inventory, shopping, events, feedback.
- Kontrakty w `contracts/` i `docs/API_CONTRACTS.md`; DB model w `docs/DATA_MODEL.md`.
- Wszystkie nazwy symboli i endpointów po angielsku; UI, komunikaty błędów i pierwsza lokalizacja po polsku.
- Server is source of truth; offline to cache + bounded, idempotent mutation queue.
- Don't add new framework/major dependency without an ADR or addendum explaining choice.

## Przepływ pracy

- Plan → implementacja minimalnego vertical slice → testy unit/integration → e2e Playwright → review security/nutrition/safety → aktualizacja statusu.
- Nie zostawiaj `TODO` w krytycznych ścieżkach jako rzekomo gotowych. Nie używaj fikcyjnych `200 OK` ani fałszywych success toastów.
- Przed każdą dużą zmianą zapisz execution plan w `docs/EXECUTION_PLAN.md` z celem, plikami, kryteriami ukończenia i testami.
- ADR-y tworzyć dla decyzji wpływających na granice domen, dane, bezpieczeństwo i kompatybilność. Zmianę zaakceptowanego ADR wyjaśnij nowym ADR.
- Nie nadpisuj zmian użytkownika i innych agentów. Przy współbieżności stosuj odrębne pliki/branch/worktree.
- Każdy ukończony slice dokumentuj w `docs/IMPLEMENTATION_STATUS.md`, załącz faktyczne komendy testowe i ich wyniki.

## Testy i QA

- Testuj arytmetykę i inwarianty na Decimal / integer minor units; nie opieraj się na float money/gram logic.
- Wykrywaj konflikty dwóch użytkowników, alergeny `unknown`, brak nutrient data, offline sync i wygaśnięcie partii.
- Import URL: SSRF defense, no private IP/redirects to private IP, finite byte/time budget, allowlist modalities, no scripts execution.
- Minimalne flow E2E: onboard two members → plan → swap/undo → guests event → batch → shopping → inventory consume.
- Po zmianie backendu: backend tests/migrations; frontend: lint/typecheck/e2e; integracja: end-to-end + test contractów.
- Jeżeli narzędzia nie są zainstalowane, raportuj ograniczenie zamiast deklarować sukces.

## Obowiązki agenta głównego

- Integruj rezultaty subagentów; prowadź rejestr decyzji i status.
- Kontroluj koszt i czas pracy; raportuj rzeczywisty postęp bez obietnic background work.
- Jeśli task jest zbyt szeroki, dostarczaj ukończony, testowalny etap, potem następny. Produkt pozostaje uruchamialny na końcu każdego etapu.
- Koniec sesji = co działa, czego brakuje, jak uruchomić, wyniki testów, następny slice.

## Review rules

Zgłaszaj w pierwszej kolejności: nieprawidłowe makro, błędy planowania porcji, ryzyko alergenu, przechowywanie jako shelf-stable bez walidacji, podwójne zużycie stanów, naruszenia licencji/Terms, SSRF, brak autoryzacji i niespójny undo.
