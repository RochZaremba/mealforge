# ADR-0012 — Separacja licencji i praw baz danych

- **Status:** Accepted (baseline architecture)
- **Date:** 2026-10-10
- **Owner:** MealForge architecture

## Context

Zewnętrzne bazy mogą mieć CC BY-SA, ODbL, prawa zastrzeżone lub warunki API.

## Decision

Model rozdziela recipe provenance, składniki/nutrient records i zewnętrzną bazę OFF. Przestrzegaj atrybucji, share-alike, ODbL (w tym skutków łączenia baz), ToS i rate limits. Licencja każdego rekordu jest obowiązkowa dla automatycznego importu. Bez uprawnienia link-only.

## Consequences

Wymaga rejestru licencji/eksportu i prawnego review przed komercjalizacją. Nie twórz nieoznaczonej zbiorczej bazy z niekompatybilnych danych.

## Alternatives

Mieszanie wszystkich baz i kopiowanie zdjęć na jeden serwer bez rights tracking — odrzucone.

## Verification

Agent odpowiedzialny dodaje testy/kontrakty potwierdzające tę decyzję w odpowiadającej jej fali z `docs/ROADMAP.md`. Zmiana decyzji wymaga nowego ADR z linkiem do tego dokumentu.
