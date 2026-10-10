# Importer-specific agent rules

- Read docs/RECIPE_SOURCES.md, config/recipe_sources.json and ADR-0004/ADR-0012 first.
- In production deny all network fetches unless a site capability is explicitly granted, documented and checked. `robots.txt` does not confer rights.
- For Mealime, Ania Gotuje, Kwestia Smaku default is link_only. Never code around CAPTCHA, blocks, authentication or paywalls.
- Pure JSON-LD parser for user-provided payload and authorized feeds; separate network adapters for approved sites.
- SSRF-safe networking: DNS/IP validation including redirects, allowlist protocols, limits, no browser code execution.
- Keep source attribution, content rights, fetched timestamp, schema errors and confidence.
