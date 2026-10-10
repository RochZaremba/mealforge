# MealForge web — WAVE-00 baseline

Responsive Polish Next.js App Router shell, live `/status` health/readiness checks, PWA manifest and a generic offline fallback. Domain features are deliberately shown as unavailable; this baseline is not a completed application.

From repository root: `pnpm install`, `pnpm --filter @mealforge/web dev`. API defaults to `http://localhost:8000`; set server-only `API_BASE_URL` when using another trusted API origin. Only `/api/health` and `/api/ready` are proxied, with no redirects, bounded timeout and `Cache-Control: no-store`.

Checks: `pnpm --filter @mealforge/web lint`, `pnpm --filter @mealforge/web typecheck`, `pnpm --filter @mealforge/web build`, `pnpm --filter @mealforge/web e2e` (API, database and browser installation required).

The service worker registers only in production over a secure context (localhost is supported). It stores only `/offline.html` and install icons. No authenticated pages, session requests, health responses or household data are cached. Saved-plan offline reading and mutation synchronization belong to WAVE-06.

Icons and illustrations are original code assets. No external photographs, fonts or telemetry scripts. Production CSP permits Next.js hydration; nonce-based strict script policy is deferred to hardening.

## WAVE-01-A: private household settings

`/household` provides real registration, login/logout, cookie-session recovery, household creation, additional members without a login, individual nullable Decimal-string goals with immutable history, and 1–12 editable daily meal slots. Breakfast/dinner repeat preferences are persisted; weekly dish planning is still unavailable. `/` reads confirmed member targets and slots from the API. Blank targets display `Nieznane`; actual zero stays zero.

The fixed `/api/v1/[...path]` proxy permits only implemented routes/methods. It forwards the original browser Origin, session Cookie, CSRF and idempotency headers. Configure server-only `APP_ENV`, `APP_BASE_URL`, `TRUSTED_ORIGINS` (comma-separated exact origins; otherwise APP_BASE_URL), and trusted `API_BASE_URL`. Development/test allow explicitly configured local HTTP; production requires explicit HTTPS browser origins, APP_BASE_URL and API_BASE_URL, and rejects session cookies missing Secure/HttpOnly/SameSite or containing Domain. The proxy caps request/response bytes at 16 KiB/256 KiB, cancels stalled body readers after five seconds, times out upstream fetches after eight seconds, rejects redirects and uses no-store.

Private data and retry keys remain in memory only. An ambiguous network/server response retains its idempotency key until a complete accepted response can be decoded. Version conflicts require reloading confirmed household state. Session expiry clears the private screen; delayed requests from a previous login cannot expire a newer session. No offline mutation queue, invitations, allergy editing or recipe catalog is claimed by this slice.
