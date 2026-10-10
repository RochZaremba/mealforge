# MealForge — zestaw startowy repozytorium dla Codexa

> Stan: **SPEC / AGENT BOOTSTRAP**. To NIE jest ukończona aplikacja. Repozytorium zawiera specyfikację produktu, decyzje architektoniczne, zadania, kontrakty i konfiguracje wyspecjalizowanych agentów. Kod aplikacji tworzy Codex w kolejnych falach.

**Cel:** self-hosted PWA do planowania jedzenia dla dwóch osób (i gości), z osobnymi kaloriami i makro, wspólnym gotowaniem, meal prepem w słoikach/pojemnikach, magazynem, wydarzeniami i automatycznymi zakupami.

## Start w 3 krokach

```bash
unzip MealForge_Codex_Agent_Kit.zip  # pomiń, jeśli już rozpakowane
cd mealforge
git init
python3 scripts/validate_kit.py
codex "$(cat PROMPT_START.txt)"
```

Możesz również otworzyć katalog `mealforge` w IDE z Codexem i wkleić zawartość `PROMPT_START.txt`. Komenda `codex` wymaga wcześniej zainstalowanego i zalogowanego Codex CLI. Jeśli dostępna instalacja nie obsługuje custom subagents, agent główny wykonuje zadania sekwencyjnie według `docs/AGENT_WORKFLOW.md`.

## Najważniejsze pliki

- [`MASTER_PROMPT.md`](MASTER_PROMPT.md) — pełny brief dla agenta głównego.
- [`AGENTS.md`](AGENTS.md) — obowiązujące zasady pisania i testowania kodu.
- [`PROMPT_START.txt`](PROMPT_START.txt) — krótki prompt uruchamiający.
- [`.codex/agents`](.codex/agents) — role agentów (TOML).
- [`docs/PRD.md`](docs/PRD.md) — wymagania i kryteria sukcesu.
- [`docs/RECIPE_SOURCES.md`](docs/RECIPE_SOURCES.md) — sposób importu z Mealime / Ani Gotuje / Kwestii Smaku i innych.
- [`config/recipe_sources.json`](config/recipe_sources.json) — maszynowy rejestr źródeł i domyślnych uprawnień.
- [`docs/ADR`](docs/ADR) — przyjęte decyzje architektoniczne.
- [`docs/ROADMAP.md`](docs/ROADMAP.md), [`tasks/`](tasks) — kolejność realizacji.
- [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md) — orchestracja, ownership i quality gates.

## Szybkie sprawdzenie zestawu

```bash
python3 scripts/validate_kit.py
```

Start zależności infra **dopiero po utworzeniu kodu przez agentów**: `docker compose -f compose.dev.yml up -d` uruchomi tylko PostgreSQL i Redis, nie uruchomi jeszcze aplikacji. W `docs/DEVELOPMENT.md` opisano docelowy `make dev`.

## Priorytet produktu

1. Jeden tydzień, dwie osoby, pięć posiłków dziennie, śniadania/kolacje powtarzalne.
2. Dobre dane żywieniowe, indywidualne porcje, alergie i twarde ograniczenia.
3. Bezpieczny i legalny katalog przepisów: linki oraz import tylko z uprawnionych źródeł; prywatne wersje użytkownika.
4. Meal prep / zapasy / lista zakupów zawsze matematycznie spójne.
5. Mało kliknięć na telefonie, niezawodna synchronizacja i cofanie zmian.

## Ograniczenia

- Żadnego hurtowego scrapowania Mealime, Ani Gotuje i Kwestii Smaku bez potwierdzonego uprawnienia. Samo JSON-LD/robots.txt nie przyznaje licencji.
- Wekowanie niskokwasowych dań nie jest równoważne zamknięciu słoika i pasteryzacji. Nie generuj parametrów konserwacji bez sprawdzonego źródła.
- AI nie wymyśla białka/węgli/tłuszczu i nie wdraża samodzielnie kodu do produkcji.

Dokumentacja źródeł i URL-i: [`docs/REFERENCES.md`](docs/REFERENCES.md).
