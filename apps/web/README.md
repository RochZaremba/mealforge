# MealForge web — WAVE-00 baseline

Responsive Polish Next.js App Router shell, live `/status` health/readiness checks, PWA manifest and a generic offline fallback. Domain features are deliberately shown as unavailable; this baseline is not a completed application.

From repository root: `pnpm install`, `pnpm --filter @mealforge/web dev`. API defaults to `http://localhost:8000`; set server-only `API_BASE_URL` when using another trusted API origin. Only `/api/health` and `/api/ready` are proxied, with no redirects, bounded timeout and `Cache-Control: no-store`.

Checks: `pnpm --filter @mealforge/web lint`, `pnpm --filter @mealforge/web typecheck`, `pnpm --filter @mealforge/web build`, `pnpm --filter @mealforge/web e2e` (API, database and browser installation required).

The service worker registers only in production over a secure context (localhost is supported). It stores only `/offline.html` and install icons. No authenticated pages, session requests, health responses or household data are cached. Saved-plan offline reading and mutation synchronization belong to WAVE-06.

Icons and illustrations are original code assets. No external photographs, fonts or telemetry scripts. Production CSP permits Next.js hydration; nonce-based strict script policy is deferred to hardening.
