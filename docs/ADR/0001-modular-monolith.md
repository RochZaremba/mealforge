# ADR-0001 — Modularny monolit zamiast mikroserwisów

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Aplikacja dla jednego gospodarstwa domowego jest silnie transakcyjna i uruchamiana na własnym VPS.

## Decision

FastAPI jako modułowy monolit, wydzielony Next.js frontend i worker. Granice: recipe, nutrition, planning, inventory, shopping, batching, auth. Wspólny PostgreSQL z jasno określonym ownership tabel.

## Consequences

Prostsze spójne transakcje i migracje, niższy koszt i mniejsza złożoność operacyjna. Nie wolno pomijać separacji domen i testów integracyjnych.

## Alternatives

Mikroserwisy i distributed saga — odrzucone jako nadmierne dla 2-5 użytkowników.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
