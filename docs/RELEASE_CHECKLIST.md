# Release checklist (do wypełnienia przed pierwszym wdrożeniem)

- [ ] Wszystkie P0 scenariusze E2E z docs/TEST_PLAN.md passed
- [ ] Household cross-tenant IDOR tests passed
- [ ] Brak sekretów i danych zdrowia w logach
- [ ] URL import SSRF/bypass/redirect negative tests passed
- [ ] Legal sources registry i licencje zweryfikowane
- [ ] OFF ODbL/share alike impacts reviewed
- [ ] Prawdziwe snapshoty kcal i historycznych porcji
- [ ] Storage safety: no unverified shelf-stable
- [ ] Inventory reservations concurrency tested
- [ ] Plan undo, offline queue conflict tested
- [ ] Backup + restore dry run passed
- [ ] Documented user data export/delete
- [ ] Lighthouse / Playwright mobile + desktop, a11y controls
- [ ] Podpisane versions/dependency scan
- [ ] Produkcyjny deploy tylko po jawnej akceptacji użytkownika
