# ADR-0009 — Izolacja household i prywatność danych

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Alergie, masa, dieta, trening i zapasy są danymi prywatnymi.

## Decision

HouseholdMember roles owner/editor/viewer; autoryzacja każdego zapytania po household scope po stronie API. Goście bez konta nie mają dostępu do rekordów. Szczególna troska o przechowywanie health/allergies; ekspozycja minimalna, export/delete.

## Consequences

Brak IDOR/cross-household leaks, wymaga E2E testów dwóch kont z odrębnymi household.

## Alternatives

Wspólne konto i sprawdzanie wyłącznie po UI — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
