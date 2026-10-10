# ADR-0014: private sessions, household scope and exact nullable targets

Status: Accepted for WAVE-01-A (2026-10-10). Extends existing identity/security decisions; no domain-boundary change.

Use argon2-cffi PasswordHasher (Argon2id) for password verification and rehash, with bounded concurrent work and PostgreSQL-backed HMAC-keyed rate buckets. This adds a focused password library to existing FastAPI, not an authentication framework. See primary API: https://argon2-cffi.readthedocs.io/en/stable/howto.html . Never implement password cryptography ourselves.

Random32-byte server sessions: only SHA256 token hashes stored; host-only HttpOnly SameSite=Lax cookie, Secure in production, expiry/revocation. Auth/session returns a session-bound HMAC CSRF token, never the cookie token. Unsafe requests require trusted Origin and JSON; authenticated mutations additionally require constant-time CSRF validation. Trust direct peer IP, not arbitrary forwarding headers. SESSION_SECRET required for private auth and production; missing auth config denies access without disabling public health endpoints. No third-party telemetry or health-data sharing.

Membership authorization applies on each endpoint and idempotency replay. Owner/editor can edit; viewer only reads. Target edits append immutable history under member row lock with expected version; slot set edits lock household. Audit has action/entity/version/actor/request ID, no password/token or health values. Atomically commit state, audit and scoped idempotency. Same key with different input conflicts. Replay rechecks auth and returns prior result; no global identifiers authorize access.

Targets are Decimal, JSON decimal strings (integer input accepted), null for unknown. True zero macro is valid; energy target zero rejected. Existing spec schema permitting only numbers is expanded explicitly for null/string precision. 4P+4C+9F is only a warning when all values are known and never overwrites targets. No recommendation, fabricated nutrient reference or implicit2700/1600 goal.

Private responses no-store. W00 worker still caches only public offline/assets. W01 invitations and original recipes remain separate next slices; no fake endpoints. Recovery/admin accounts, production HTTPS hosting and offline mutation queue are not claimed by this ADR.
