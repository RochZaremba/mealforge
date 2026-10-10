# Development — runnable WAVE-00 baseline

WAVE-00 implementuje rzeczywiste API/DB/web; funkcje żywieniowe w WAVE-01+ wymagają kolejnych fal. Nie używamy mock API do statusu. Wymagania: Docker+Compose, uv, pnpm10.28.2, Node22 LTS. uv automatycznie instaluje Python3.12. Sekrety lokalne tworzy make init-env bez ich wyświetlania.

## Docker (pełny baseline)
```bash
make init-env
make dev
# http://localhost:3000 oraz http://localhost:3000/status
# http://localhost:8000/health oraz /ready
make stop
```
Compose buduje API i web, migracja kończy się przed API, DB jest prywatny poza portem loopback w development. make stop zachowuje dane. Nie uruchamiaj jednocześnie serwerów local i Docker na tych samych portach. Domyślny POSTGRES_PORT=5432; ustaw wolny port oraz zgodny DATABASE_URL w prywatnym .env w razie konfliktu. Ta sesja używa55432.

## Lokalne serwery
```bash
make init-env
make deps
make install
make migrate
make dev-local
```
Next dev oraz API na loopback; Ctrl+C zatrzymuje obydwa procesy. Nieoczekiwane zakończenie serwera daje błąd. Pełne testy PWA wymagają production build; make e2e uruchamia własny production server.

## Quality gates
```bash
make validate-kit
make test
make migration-test
make check-contract
make lint
make typecheck
make build
pnpm --filter @mealforge/web exec playwright install chromium
make e2e
```
make test używa izolowanych UUID baz PostgreSQL; potrzebne CREATE DATABASE. Brak konfiguracji DB powoduje jawne pominięcie integration przez pytest; takie pominięcie nie jest green wave gate. Migration test nie zmienia skonfigurowanej bazy — używa i usuwa wyłącznie nową bazę testową. OpenAPI eksport: make openapi; drift: make check-contract. contracts/openapi.yaml zawiera JSON (legalny YAML), generowany wyłącznie z FastAPI. Zarys przyszłych endpointów pozostaje w API_CONTRACTS.

Jeśli masz już uruchomiony production web/API, użyj PLAYWRIGHT_NO_SERVER=1 make e2e. make e2e normalnie wymaga wolnego portu3000; nie podmienia serwera developerskiego. API musi być po migracji; .env jest wczytywany przez uv.

## Backup development
Przygotuj prywatny plik hasła (chmod600), ustaw BACKUP_PASSPHRASE_FILE na jego absolutną ścieżkę. Nie umieszczaj hasła w CLI/historii/repo.
```bash
make backup
python3 scripts/decrypt_backup.py backups/<plik>.dump.enc /tmp/mealforge-restore.dump
```
Backup pg_dump custom-format jest szyfrowany AES256/PBKDF2 i uwierzytelniony HMAC; weryfikacja następuje przed odszyfrowaniem. Skrypt nie nadpisuje istniejącego output. pg_restore testuj wyłącznie na nowej, disposable bazie. Backupy ignorowane przez Git; eksport odszyfrowany jest prywatny i wymaga usunięcia po teście.

## Release
Brak automatycznego produkcyjnego deployu. TLS, klucze/secrets custody, harmonogram backupów, poza-hostowy storage, pełne restore drill oraz wszystkie P0 nadal wymagają release checklist. RECIPE_REMOTE_IMPORT_ENABLED=false; rejestr config/recipe_sources.json blokuje automatyczne fetch bez praw.
