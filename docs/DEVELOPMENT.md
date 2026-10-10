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

## Invitations W01-B (PR #3 merged)
On /household the owner selects an existing non-login resident and editor/viewer access, creates a 24-hour single-use code and passes it privately. The recipient registers/logs in on their own account and enters the code in the join form. No email is sent. Owner-only account controls can revoke or restore access; resident participation, targets and history remain. Viewer sees profiles and slots without edit controls. The canonical owner cannot be demoted or revoked. Codes stay in ephemeral memory and JSON bodies, with no URL or persistent browser storage.

## Private recipes W01-C (PR #4 merged; gates passed)

Open /recipes after logging in. The current household selection is shared with /household and Today, retained only in memory and rechecked with the server. Create a private recipe by declaring ingredient amounts/units/states, writing your own instructions and confirming authorship of your contribution. Edits append immutable versions; history and list pages are reachable. Empty amount means unknown, not zero. Recipes remain drafts with unknown nutrition/allergens/yield/storage and cannot enter a planner.

The separate demo button requires explicit confirmation. It creates a new owned household with two sample targets2700/1600 (all macros unknown), five slots and three original MealForge drafts. No demo is seeded by startup, signup or real household creation. Existing real goals/history remain unchanged. Original text is CC0 only within its declared scope; new private user edits have unknown license and retain original attribution. No external recipe fetch is activated.

`make recipe-fixture-test` requires running Docker and verifies the original root fixture, installed API resource, audited server loader and actual API container equality. Missing or altered runtime originals fail demo creation atomically. Use IMPLEMENTATION_STATUS and TEST_REPORT for actual integration/CI/merge gates. W02 nutrition, W03 planning and later kitchen/offline functions are not completed.

## Private source links W02-A (integration gates in progress)

On /recipes, select a household and use “Dodaj link”. Supply an HTTPS address, your own title and optional own note; confirm authorship only of your contribution. The server saves an immutable private bookmark. Viewer can read details; only editor/owner can save. Lists have bounded pagination. Source opens only after the explicit link click, with no page previews or background fetching. No edit/delete controls exist in A.

Saving a URL does not create a recipe, determine nutrition/allergens/storage or grant import rights. Known source IDs merely classify exact domains. The opening URL keeps its fragment; deduplication ignores it. Source-registry check dates come from the packaged configuration, not a new Terms audit. `make source-registry-test` compares repository/installed registry with the audited loader in the actual Docker API; tampered resources fail closed. Full W02 parser, nutrition calculation and provider adapters remain future slices.
