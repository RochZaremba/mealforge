# Development — runnable baseline and W01-A household slice

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

## Household slice W01-A
Open /household after make dev. Register your account and explicitly log in, create a household, add the second non-login resident, edit separate nullable targets and history, and save1–12daily meal slots/repeat settings. No implicit2700/1600 goals. This is persisted onboarding, not a generated meal plan. Invitations and original recipe catalogue remain next slices.

APP_BASE_URL/TRUSTED_ORIGINS must match browser origins on both API/web; local defaults allow localhost3000 and127.0.0.1:3000. SESSION_SECRET comes from the private .env. Production APP_ENV requires strong secrets/HTTPS; production deployment remains unapproved. Logs omit API access paths and PostgreSQL bound values. make privacy-test performs a real disposable-db duplicate error and checks that its private sentinel is absent while the generic error is present. CI-only --configure-ci refuses other environments/databases. For managed production DB set equivalent privacy settings with the DBA before release; never enable private statement logging for diagnostics.

make backup-test now compares every public table using an exported consistent snapshot; private values are not printed. W01 actual restore proof includes11tables/224rows, including synthetic goals and history, sessions/audit/idempotency. Evidence screenshots contain synthetic QA accounts and targets only.
