# Observability i diagnostyka

Minimalne cele po WAVE-00:

- `request_id`, `household_id` pseudonimizowane (lub hashing), domain command, duration, status; unikać logowania zdrowia, alergii, adresów i żywieniowych payloadów.
- `planning_solver_ms`, `planner_infeasible_count`, `nutrition_incomplete_count`, `inventory_conflict_count`, `import_policy_blocks`, `import_http_failures` i `pwa_sync_conflicts`.
- Alerty tylko dla realnych błędów API/DB, nie dla planera poprawnie raportującego brak rozwiązania.
- W raporcie performance podaj rozmiar katalogu i warunki testu, bez fikcyjnych P95.
- Tracing importowanych źródeł nigdy nie loguje pełnych treści zewnętrznych artykułów ani tokenów.
- Privacy opt-in dla danych produktowych; no hidden third-party analytics SDK by default.
