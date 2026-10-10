# ADR-0003 — Receptury wersjonowane i źródło praw

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Źródła mogą zmieniać strukturę, liczby porcji i prawa; potrzebna historia obliczeń.

## Decision

Canonical Recipe oraz immutable RecipeVersion i RecipeSource (URL, autor, license, rights, fetchedAt, sourceHash, attribution, trustStatus). Zewnętrzny rekord najpierw draft/quarantine. Planner używa tylko validated version.

## Consequences

Można odtworzyć historię bilansu i usunąć dane źródłowe z ograniczeniami. Duplikaty po canonical URL + fingerprint składników, bez kopiowania chronionych instrukcji.

## Alternatives

Bezpośrednia ingerencja w oryginalny zewnętrzny przepis bez wersji — odrzucona.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
