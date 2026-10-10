.PHONY: help init-env validate-kit deps install dev dev-local stop test lint typecheck e2e migrate seed migration-test openapi check-contract build backup backup-test
UV ?= uv
PNPM ?= pnpm
COMPOSE = docker compose --env-file .env -f compose.dev.yml
help:
	@echo "init-env install deps migrate dev-local | dev (full Docker) | test lint typecheck e2e build backup"
init-env:
	python3 scripts/init_env.py
validate-kit:
	$(UV) run --directory apps/api python ../../scripts/validate_kit.py
install:
	$(UV) sync --directory apps/api --frozen
	$(PNPM) install --frozen-lockfile
deps: init-env
	$(COMPOSE) up -d --wait postgres
dev: init-env
	$(COMPOSE) up --build -d --wait
stop:
	$(COMPOSE) stop
migrate:
	$(UV) run --directory apps/api --env-file ../../.env alembic upgrade head
seed:
	$(UV) run --directory apps/api --env-file ../../.env python -m mealforge.seed
migration-test:
	$(UV) run --directory apps/api --env-file ../../.env bash ../../scripts/test_migrations.sh
openapi:
	$(UV) run --directory apps/api python -m mealforge.openapi --output ../../contracts/openapi.yaml
check-contract:
	$(UV) run --directory apps/api python -m mealforge.openapi --output ../../contracts/openapi.yaml --check
test:
	$(UV) run --directory apps/api --env-file ../../.env pytest
	python3 scripts/test_backup_integrity.py
	$(UV) run --directory apps/api python ../../scripts/test_nutrition_contract.py
lint:
	$(UV) run --directory apps/api ruff check .
	$(PNPM) lint
typecheck:
	$(UV) run --directory apps/api mypy src
	$(PNPM) typecheck
build:
	$(PNPM) build
e2e:
	$(UV) run --project apps/api --env-file .env $(PNPM) e2e
dev-local:
	python3 scripts/dev.py --uv $(UV) --pnpm $(PNPM)
backup-test:
	$(UV) run --project apps/api --env-file .env python scripts/test_backup_restore.py
backup:
	python3 scripts/backup.py
