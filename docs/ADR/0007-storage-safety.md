# ADR-0007 — Rozdzielenie refrigerated, frozen i verified shelf-stable

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Użytkownik planuje słoiki do meal prepu, istnieje ryzyko błędnego utożsamienia zwykłej pasteryzacji z bezpiecznym wekowaniem dań niskokwasowych.

## Decision

Typ `StorageMethod`: refrigerated_ready_meal, frozen_ready_meal, verified_canned_food. Ostatni tryb wymaga certyfikowanego source recipe/process ID i zgodności warunków; zwykła generowana receptura nie może stać się shelf-stable. Domyślnie krótkie, bezpieczne zakresy dla lodówki lub zamrażanie.

## Consequences

Mniej ryzyka zatrucia, wymaga UX jawnie pytającego o sposób przechowywania. Etykiety zawierają provenance i datę.

## Alternatives

Automatyczne przewidywanie ciśnień/czasów wekowania przez LLM — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
