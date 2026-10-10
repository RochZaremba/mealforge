# ADR-0010 — Offline-first read, bounded mutation queue i historia planów

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

W sklepie czasem nie ma Internetu; pomyłki przy zamianie posiłku muszą dawać się wycofać.

## Decision

Offline cache last-known plans/recipes/shopping; mutacje lokalne oznaczane pending, z idempotency key i expectedVersion; server validates, conflict -> retry/manual resolution. Undo plan events requires compensating operations, not silent overwrite of inventory.

## Consequences

Niezawodniejsza obsługa i jawność statusu. Offline optimizer nie jest wymagany w MVP.

## Alternatives

LocalStorage jako jedyne źródło stanu i silent last-write-wins dla magazynu — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
