# Optimizer-specific agent rules

- Read docs/OPTIMIZER_SPEC.md, docs/NUTRITION_ENGINE.md and ADR-0006.
- Solver must be deterministic for fixed input and seed; no LLM-created nutrition values.
- Hard constraints: allergens, excluded ingredients, safety storage, portions in stock, blocked meals, events.
- Use Decimal / scaled integers; report infeasibility and soft trade-offs honestly.
- Unit tests for 2700/1600 kcal example, leftovers, guest count, swap/undo, macros tolerances.
