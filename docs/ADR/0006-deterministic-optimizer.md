# ADR-0006 — Deterministyczny solver z twardymi ograniczeniami

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Wiele opcji: kalorie, makro, czas, zapasy, liczba osób, batch/food safety.

## Decision

Preferuj OR-Tools CP-SAT dla skwantowanych porcji i binarnych decyzji. Hard constraints allergy/storage/availability/locks/attendees; soft goals kcal ±5% i makro ±10% jako cele konfigurowalne, a nie zawsze osiągalne. Stały seed, limit czasu, raport infeasible/fallback.

## Consequences

Zachowanie jest reprodukowalne i możliwe do testowania; użytkownik widzi kompromisy. LLM może wyjaśniać, nigdy definiować nieistniejące makro.

## Alternatives

Random planner lub LLM-only solver — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
