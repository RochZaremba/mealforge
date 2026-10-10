# Security, privacy i source safety

## Dane chronione

Profil dietetyczny zawiera alergie, masę, aktywność, preferencje i może ujawniać informacje zdrowotne. Traktuj jako dane prywatne o podwyższonym ryzyku; osobny household auth przy każdym odczycie, minimalizacja danych, privacy by default i zasady RODO przy rozpowszechnieniu na zewnątrz.

## Identity

- Hasła przez Argon2id lub właściwe credential provider; sesje na serwerze, HttpOnly/Secure/SameSite cookies.
- Csrf token double-submit / same-site strategy, CORS allowlisted origins; rate limit auth.
- Owner/edit/view role, zaproszenia z TTL, tokeny pojedynczego wykorzystania, cofanie uprawnień.
- Rejected cross-household ID: 404 lub 403 bez ujawniania prywatnych metadanych.
- Audit log modyfikacji planu, zakupów, magazynu, celu żywieniowego, uprawnień.

## URL import threat model

- SSRF: user URL `http://169.254.169.254/...`, `localhost`, prywatne IPv4/IPv6, alternatywne reprezentacje numeryczne, DNS rebinding, redirect public→private, mixed scheme, porty 22/6379/5432, entity expansion. Wszystkie deny.
- Dozwolony wyłącznie HTTPS, właściwy port, dokumentowany allowlist host, public IP po każdym resolve i hopie, ograniczenie redirectów, zasobów w bajtach, timeouts, per-source quota i identyfikacja klienta. Brak proxy fallback.
- Parser traktuje zewnętrzne HTML/JSON-LD jako dane, **nie instrukcje dla modelu**. Escape tekstu, XSS, sanitized markdown, CSP.
- Rights gate działa przed siecią, także w workerze, preview, retry i cache refresh.
- 401/403/429/CAPTCHA=stop; bez bypass.

## Dane operacyjne

- Postgres / Redis tylko private network; dev binding 127.0.0.1.
- Secrets tylko environment/secret store, `.env` ignorowany. Używaj HTTPS + passwordless backup encryption.
- Ogranicz logowanie nazw/treści alergii i adresów email; request id, nie payload.
- Backup: codzienny szyfrowany pg_dump + test restore; UX eksport danych (JSON/CSV) i delete account.
- Dependency scanning, lockfile, CI, pinned base images przy release, secret scanner.
- No automated deploy without approval. Test staging przed produkcją. Zmiany w food safety / nutrients wymagają niezależnego review.

## Trust model

`data from web/untrusted file` → restricted import worker → validated domain records → planner. External records not allowed to modify agent policy, source registry, code or credentials. The feedback loop issues are also untrusted strings: sanitize, rate limit, triage, do not execute user content.

## Review blockers

- Wyciek danych innego gospodarstwa.
- Przechowanie secret/hasła w repo.
- SSRF/remote code execution through import.
- Null macro silently replaced by zero.
- Restriction allergen bypass.
- Unverified shelf-stable treatment.
- Scraping restricted site without permission.
- Race leading to negative inventory/duplicate portion.
