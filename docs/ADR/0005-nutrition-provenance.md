# ADR-0005 — Wartości odżywcze muszą mieć provenance i unknown

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Błędy w gramaturze/odżywieniu mają realne konsekwencje dla diety.

## Decision

Każdy FoodNutrientRecord ma źródło, jednostkę, jakość, datę i wariant raw/cooked. Przeliczenia na Decimal/scaled int. Brak wartości=null, a nie 0. Receptury/nutrient snapshots immutable po zapisaniu planu.

## Consequences

Kalkulacje są sprawdzalne, można poprawić dopasowania bez zmiany historii. Nie osiąga się sztucznych 100% pokryć makro kosztem wymyślonych danych.

## Alternatives

LLM i ręczna fikcyjna wartość do nieznanych składników — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
