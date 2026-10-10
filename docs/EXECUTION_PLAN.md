# Wykonywany plan implementacji

## Aktualna fala

WAVE-00 (do rozpoczęcia przez Codexa).

## Pierwszy vertical slice

- Czysty checkout daje `make dev` z rzeczywistym `/health`, frontendem i PostgreSQL.
- Własne seed data i jedna przykładowa household API endpoint.
- CI z rzeczywistą bramką zamiast dummy echo.

## Plan równoległości

Architect uzgadnia DB/contracts, Backend buduje usługę, Frontend buduje shell, QA ustawia testy. Reviewer/security weryfikują wynik. Nie edytować równolegle tych samych plików.

## Exit criteria

Rzeczywiste komendy i ich wyniki opisane w `docs/TEST_REPORT.md`. Jeśli brak środowiska albo error, raportuj blokadę i nie oznaczaj jako DONE.
