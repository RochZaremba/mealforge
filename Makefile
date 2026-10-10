.PHONY: validate-kit deps help
help:
	@echo "make validate-kit : verify specification and agent config"
	@echo "make deps         : start PostgreSQL + Redis (after cp .env.example .env and editing password)"
	@echo "Run Codex to create application code: codex \"$$(cat PROMPT_START.txt)\""
validate-kit:
	python3 scripts/validate_kit.py
deps:
	docker compose --env-file .env -f compose.dev.yml up -d
# Agents add real dev/test commands in WAVE-00; do not add fake green checks.
