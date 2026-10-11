# Permission-gated recipe import (WAVE-02)

Implement a **pure parser** for user-supplied schema.org/Recipe JSON-LD separately from permissioned network adapters. `config/recipe_sources.json` defaults protected domains to `link_only`; any network mode requires documented reviewer approval. Fixtures are synthetic.

W02-A bookmark shape validation is packaged in the modular API as
`mealforge.importers.url_policy`, rather than a separate installable dependency.
It preserves a validated opening URL and a fragment-free canonical identity,
and classifies exact registry hosts without DNS, HTTP, permissions or license
inference. It is not a transport SSRF gate: future fetching requires independent
rights, DNS/address and redirect validation. JSON-LD parsing and network adapters
remain later slices.

W02-B1 adds the pure bounded own JSON-LD preview in `apps/api/src/mealforge/importers/jsonld.py`; the authenticated transient endpoint lives in `preview.py`. No JSON-LD expansion, context/reference retrieval, HTML parsing, scripts, images or nutrient inference. No source/recipe persistence in B1; B2 must preserve immutable import origin explicitly before enabling save.
