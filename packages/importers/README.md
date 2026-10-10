# Permission-gated recipe import (WAVE-02)

Implement a **pure parser** for user-supplied schema.org/Recipe JSON-LD separately from permissioned network adapters. `config/recipe_sources.json` defaults protected domains to `link_only`; any network mode requires documented reviewer approval. Fixtures are synthetic.

W02-A bookmark shape validation is packaged in the modular API as
`mealforge.importers.url_policy`, rather than a separate installable dependency.
It preserves a validated opening URL and a fragment-free canonical identity,
and classifies exact registry hosts without DNS, HTTP, permissions or license
inference. It is not a transport SSRF gate: future fetching requires independent
rights, DNS/address and redirect validation. JSON-LD parsing and network adapters
remain later slices.
