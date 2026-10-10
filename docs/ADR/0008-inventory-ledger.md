# ADR-0008 — Event ledger + rezerwacje zapobiegające podwójnemu zużyciu

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Dwie osoby mogą w tym samym czasie kupować, planować i zjadać dania.

## Decision

Immutable InventoryTransaction ledger per lot; `on_hand`, `reserved`, `available=on_hand-reserved` z transakcyjną kontrolą w DB. Unique idempotency keys; lock version/row for reserve/consume; plan zmian odwracalny eventami kompensującymi; zero oversell.

## Consequences

Audyt i undo bez nadpisywania przeszłości. Testy concurrency są obowiązkowe.

## Alternatives

Proste aktualizowanie `quantity` bez historii i optimistic checks — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
