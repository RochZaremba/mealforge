# ADR-0011 — Uczenie preferencji oddzielone od zmian kodu

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Użytkownicy chcą lepsze rekomendacje, ale nie wolno automatycznie zmieniać zasad bezpieczeństwa, celów i aplikacji produkcyjnej.

## Decision

Preferences feedback per user/household, explainable rank weights with opt-in/out & reset. Engineering loop via issues/test/code review; AI może tworzyć PR, lecz human approval przed deploy.

## Consequences

Bezpieczeństwo danych i audyt zmian, brak samodzielnych niekontrolowanych deploy.

## Alternatives

Self-mutating source/prod policy, automatyczna publikacja kodu z AI — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
