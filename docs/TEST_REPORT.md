# Test report — 2026-10-10

| Wave | Command | Exit | Actual result |
|---|---|---|---|
| bootstrap | python3 scripts/validate_kit.py | 0 | 139 passed, 0 failed, 1 skipped (brak jsonschema) |
| W00 tooling | /tmp/mealforge-tools-venv/bin/python scripts/validate_kit.py | 0 | 144 passed, 0 failed, 0 skipped po instalacji jsonschema/PyYAML |
| W00 database | docker compose --env-file .env -f compose.dev.yml up -d --wait postgres | 0 | PostgreSQL 16 zdrowy, bind 127.0.0.1:55432 |

API/web/E2E/migration/backup acceptance: PENDING integration. Domain A01–A15 nie są na tym etapie zakończone.

Audit nutrition/integrations: istniejące syntetyczne fixtures nie zawierają fikcyjnych wartości nutrient; fetch wszystkich źródeł wyłączony. Przed W01 kontrakt makro wymaga null; przed W02 import contract musi wymusić link-only/draft/provenance.
