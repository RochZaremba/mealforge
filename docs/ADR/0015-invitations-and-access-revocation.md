# ADR-0015: private one-use invitations and separate account access

Status: Accepted for W01-B, 2026-10-10. Extends ADR0009 and0014; no new dependency or external messaging.

Guest or unlinked resident nutrition is distinct from login access. Add access_enabled/access_version on HouseholdMember, keep active for resident participation. All membership authorization, household listing and mutation/idempotency replay require active+access_enabled and authenticated user match. Owner may change editor/viewer or revoke access with version guard, cannot self-demote/revoke. Revocation does not remove profile targets or change portions/participation. Household owner identity is protected using owner_user_id, not merely a role label.

Owner creates invitation for an unlinked non-guest member in the same household, or a new resident. Role only editor/viewer. TTL24h, random32-byte private nonce, invitationUUID, HMAC-SHA256 with domain separate from sessions/CSRF, SHA256token hash stored. Raw token returned only in creation response, submitted on accept in JSONbody; no email/URL/query, logs or audit. Idempotency record stores reference/metadata rather than raw token, reconstructs only for authorized owner. Secret rotation detects mismatched derivation and fails closed; user must issue a new invitation.

Acceptance is authenticated+CSRF+idempotency and locks invitation/member to consume once, atomically linking recipient to existing profile or creating one newmember. Replays reauthorize current account access; revoked access cannot be restored by stale replay. Samekey retries deterministic, newkey reusing consumed/expired/revoked token rejected; guest linking forbidden. Audit metadata carries action/entity/version only. Revoke invitation separately from membership access; list never returns raw code/hash/nonce. Privacy API/body bounds and no-store remain unchanged.

Validation: actualPG races/TTL/guest/IDOR/owner/current-role checks, two-browser-account onboarding and viewer/revoked access; targets/history unchanged by account link/revocation. Registration recovery/export/delete remain later hardening; no production deployment.
