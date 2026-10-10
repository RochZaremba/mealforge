# Roadmapa implementacji / kolejność fal

**Każda fala kończy się działającą pionową funkcją**, nie listą przypadkowych endpointów. Agent główny aktualizuje `docs/EXECUTION_PLAN.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/TEST_REPORT.md`.

| Fala | Zależność | Funkcje | Gate |
|---|---|---|---|
| WAVE-00 | start | pnpm/uv, DB, API, web, Docker dev, healthcheck, migrations, CI | nowy checkout uruchamia baseline |
| WAVE-01 | W00 | identity/household, profile A/B, 5 slots, seed oryginalnych przepisów | E2E logowanie/onboarding / podgląd |
| WAVE-02 | W01 | nutrition engine, conversions, allergen gates, canonical recipe + link-only imports, pure JSON-LD parser | złote testy makro, zero unknown-as-zero |
| WAVE-03 | W02 | tydzień, pinned repeat, plan versions, swap, undo, preview of guest/no-cook events | scenariusze 1/2/4/5/6 |
| WAVE-04 | W03 | batch cooking, jars, inventory lots, FEFO, reservations, shopping diff | brak double allocation, kitchen tests |
| WAVE-05 | W04 | optimizer with bounded solve, One Click Week, budget where known, fridge rescue, low-waste | hard constraints/infeasible explanation |
| WAVE-06 | W05 | PWA offline queue, prefs feedback, QR labels, review, hardening, backup | offline and restore e2e + threat model |
| WAVE-07 | W06 | 100+ verified local recipes, permitted source adapters, quality scoring, analytics, optional training inputs | license audit + quality sampling |

Minimalna używalna wersja to WAVE-00 do WAVE-04. Późniejsze inteligentne moduły nie mogą ukrywać błędów w stanach zapasów lub wartościach żywieniowych.

**Przy zmianie roadmapy** wymagana aktualizacja ADR i impact analysis. Import z witryn komercyjnych: link-only default nigdy nie podlega presji liczby przepisów.
