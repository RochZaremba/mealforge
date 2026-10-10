# MealForge — zestaw startowy repozytorium dla Codexa

> Stan: **WAVE-00 oraz cała WAVE-01 scalone po testach i review**. Działają API/DB/web, logowanie, prywatne gospodarstwa, cele i historia domowników, ustawienia posiłków, zaproszenia, zarządzanie dostępem, wersjonowane własne przepisy i jawne osobne demo. W02-A integruje prywatne linki bez pobierania stron; odbiór w toku. Obliczenia żywieniowe, planowanie i kuchnia pozostają kolejnymi etapami; aplikacja nie jest jeszcze gotowym produktem.

**Cel:** self-hosted PWA do planowania jedzenia dla dwóch osób (i gości), z osobnymi kaloriami i makro, wspólnym gotowaniem, meal prepem w słoikach/pojemnikach, magazynem, wydarzeniami i automatycznymi zakupami.

## Uruchomienie baseline

```bash
make init-env
make dev
# http://localhost:3000/status
# http://localhost:3000/household — rejestracja i prywatne gospodarstwo
# http://localhost:3000/recipes — własne przepisy i osobne demo (W01-C)
```

Docker Compose buduje realny API/web i migruje PostgreSQL. Dla lokalnego developmentu i quality gates: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Faktyczny zakres i testy: [status](docs/IMPLEMENTATION_STATUS.md), [test report](docs/TEST_REPORT.md).

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

`make deps` uruchamia wyłącznie PostgreSQL; `make dev` pełny baseline. Dane zewnętrzne nie są wymagane do uruchomienia.

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
