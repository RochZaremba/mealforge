# ADR-0004 — Import sieciowy tylko z potwierdzoną możliwością

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Mealime ma ograniczenia automatycznego pozyskiwania, polskie serwisy zastrzegają prawa. JSON-LD jest formatem, nie licencją.

## Decision

Default deny. Registry steruje `link_only`, `user_supplied`, `authorized_api`, `authorized_fetch`. Mealime, Ani Gotuje, Kwestia Smaku default link-only. Parser schema.org działa bez sieci na danych dostarczonych przez użytkownika; sieć dostępna tylko przez approved rights-gate, robots i ToS recheck + SSRF/rate limits.

## Consequences

Brak nieautoryzowanego mass harvest, mniejszy problem copyright i niezależność od serwisów. Użytkownik nadal może dodawać własne przepisy i źródłowe linki.

## Alternatives

Automatyczny crawler/scraper chronionych witryn i anti-bot bypass — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
