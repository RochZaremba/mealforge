# Contributing / zasady zmian agentowych

1. Przeczytaj `AGENTS.md`, `MASTER_PROMPT.md` i odpowiadające ADR-y.
2. Wybierz jedno zadanie w `tasks/WAVE-XX.md` i zapisz zakres w `docs/EXECUTION_PLAN.md`.
3. Pracuj na osobnym branch/worktree. Nie zmieniaj plików współdzielonych z innym agentem bez koordynacji.
4. Dostarcz kod + test + migrację + aktualizację dokumentacji + raport realnego wykonania.
5. Source import, nutrition i food storage to obszary krytyczne: bez pozytywnego reviewer/security gate nie merge.
6. Każdą nową bibliotekę z licencją i każde API dokumentuj w `docs/RECIPE_SOURCES.md` / ADR, jeśli wpływa na architekturę.
7. Dane seed nie mogą być skopiowane z chronionego przepisu ani zawierać udawanych wyników odżywczych.

## Branch naming

`feat/wave-XX-short-feature`, `fix/module-bug`, `docs/adr-XXXX-topic`.

## Commit / PR

Opis z czego wynika zmiana; testy i wyniki; screenshot dla UI; zmiany kontraktów; migration plan. Produkt nie może używać mock API w production bez wyraźnego oznaczenia incomplete.
