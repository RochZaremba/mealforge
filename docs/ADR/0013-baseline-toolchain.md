# ADR-0013 — Baseline tooling and privacy-safe PWA shell

- Status: Accepted
- Date: 2026-10-10
- Owner: integration lead

## Decision
Implement accepted FastAPI/SQLAlchemy/Alembic/PostgreSQL and Next.js architecture with Python 3.12, uv project lock, pnpm 10 workspace lock and Node.js 22 containers/CI. pytest/httpx test API, Ruff/mypy check Python, ESLint/TypeScript check web, Playwright checks real services. Standard JSON responses/problems expose no DSN. A tiny first migration stores only non-private reference data; no demo household is publicly readable.

The W00 PWA worker caches only its generic offline fallback and local icons; never cache API responses, session content or private navigation. Saved plans and bounded mutation queue remain W06. Root CI uses service PostgreSQL and generated OpenAPI drift checks. Runtime schema remains SQLAlchemy/Alembic.

## Consequences
No new application framework. Two lockfiles correspond to distinct runtimes. Health and readiness are public, private endpoints require sessions from W01. Development Docker uses loopback ports; production TLS/release controls remain release checklist. New dependency licenses recorded in lockfile metadata and respective project manifests; external recipe APIs remain disabled.
