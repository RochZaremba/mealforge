# Development i deployment instructions

## Status

Starter to dokumentacja/konstrukcja dla Codexa. `compose.dev.yml` startuje **tylko** PostgreSQL + Redis. `apps/api` i `apps/web` mają powstać w WAVE-00/01.

## Wymagania

- Linux/macOS (Arch/Ubuntu OK), Git, Python 3.11+, Docker + Compose, Node.js LTS + pnpm, opcjonalnie uv, Codex CLI.
- Jeśli Codex CLI nie jest dostępny, otwórz katalog w IDE z Codexem i wklej `PROMPT_START.txt`.

```bash
cd mealforge
python3 scripts/validate_kit.py
cp .env.example .env
# Zmień POSTGRES_PASSWORD, DATABASE_URL i SESSION_SECRET w .env.
docker compose --env-file .env -f compose.dev.yml up -d
codex "$(cat PROMPT_START.txt)"
```

### Po ukończeniu WAVE-00 (do zaimplementowania przez agentów)

Oczekiwane komendy / standard:

```bash
make dev          # Next + FastAPI + PostgreSQL/Redis dev deps
make test         # unit, integration
make lint         # ruff/eslint
make typecheck    # mypy/tsc
make e2e          # Playwright
make migrate      # Alembic upgrade head
make backup       # pg_dump backup
```

Powyższe make targets NIE istnieją w zestawie i **są wymaganiami do wykonania przez agentów**, nie działającymi obecnie poleceniami. Nie zgłaszaj ich jako green.

## Self-hosting release criteria

- Oddzielny `.env.production`, silne sekrety, backup szyfrowany, TLS, secrets management, izolowana sieć postgres/redis, brak publicznych portów DB.
- Test restore na kopii, HTTP health + readiness, Log rotation, CORS whitelist, CSRF, downtime-friendly migrations.
- Uprawnienia only needed, nonroot containers, pinned images; wybór domeny przez użytkownika.

## Import src

Zdalny import `RECIPE_REMOTE_IMPORT_ENABLED=false` domyślnie. Włączenie tylko po source review i certyfikacji domeny w registry, nie globalny przełącznik do scrapowania.
