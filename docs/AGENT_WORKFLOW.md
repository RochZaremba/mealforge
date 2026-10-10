# Orkiestracja agentów i kryteria bramkowania

## 1. Agent główny prowadzi integrację

Zaakceptowany plan w `docs/EXECUTION_PLAN.md` i aktualny stan w `docs/IMPLEMENTATION_STATUS.md` są źródłem prawdy o postępie. Agent główny przypisuje jednego właściciela na katalog lub plik i *scalanie zawsze robi sam*. Współdzielone kontrakty/API/ADR aktualizuje tylko owner uzgodniony na daną falę. Jeśli lokalny Codex nie wspiera custom subagents, prowadź identyczną kolejność ról sekwencyjnie.

## 2. Główne role

| Agent | Owner | Bramka |
|---|---|---|
| `architect` | kontrakty, model, ADR | spójność domen i migracji |
| `backend` | `apps/api` | testy auth, UoW, API i DB |
| `frontend` | `apps/web` | typy, a11y, Playwright |
| `nutrition` | `packages/optimizer` / kalkulator | edge cases i znane wyniki referencyjne |
| `integrations` | `packages/importers` | licencje, SSRF, pipeline jakości |
| `qa` | testy i raporty | niezależne E2E i performance |
| `security` | audyt | blockers auth/privacy/import/storage |
| `ux` | audyt UI | użyteczność i dostępność |
| `reviewer` | niezależne code review | final acceptance |

## 3. Zasady pracy równoległej

- Po uzgodnieniu kontraktu możesz równolegle uruchomić backend (moduły identity), frontend (shell), nutrition (czysta logika), integrations (pure JSON-LD parser) i QA (fixtures/test harness).
- Nie zaczynaj dwóch zmian w tej samej migracji / OpenAPI / pliku ADR. Równoległe branch/worktree, małe PRy i integracja po zielonych bramkach.
- Security i reviewer najlepiej aktywować po pierwszym działającym vertical slice; udostępnij im artefakty testów oraz commit.
- Lead nie deleguje na siłę wszystkiego: zadania zależne kolejność według `docs/ROADMAP.md`.
- Zewnętrzne importery z prawami niewiadomymi nie blokują MVP: dostępna zawsze funkcja save URL + ręczny przepis.

## 4. Quality gates per wave

1. Wytwarzana funkcja ma konkretne kryteria w `tasks/WAVE-XX.md`.
2. Typy/lint/testy jednostkowe i integracyjne wykonane rzeczywiście, log wyników.
3. E2E wymaganych flow; brak pustych przycisków.
4. Food safety, nutrition provenance, household isolation i source licensing ocenione przez kogoś innego niż autora.
5. Szybki manual test na mobile i desktop, screeny w `docs/evidence/` opcjonalnie.
6. Zmiana udokumentowana w `docs/IMPLEMENTATION_STATUS.md`, `docs/TEST_REPORT.md`.
7. Nie wdrażaj produkcji automatycznie. Deploy tylko po jawnej decyzji użytkownika.

## 5. Wzór wiadomości delegacyjnej

> Agent `nutrition`: pracuj wyłącznie w `packages/optimizer` i powiązanych testach. Zweryfikuj WAVE-03, ADR-0005/0006; napisz implementację skalowania porcji i walidacji `unknown`. Nie edytuj `apps/api` ani kontraktów. Zgłoś testy, braki, interfejs do integracji.

## 6. Feedback / samodoskonalenie

Każdy slice przechodzi `code → tests → browser check → metrics → review → fixes → tests`. Przed kodem sprawdź problem statement; po kodzie porównaj efekt z kryteriami. Opcjonalne AI może generować *propozycję* PR, ale nigdy samo modyfikować produkcyjnych reguł żywnościowych, automatycznie publikować nowych licencjonowanych przepisów ani wdrażać PR.

## 7. Finish contract

Raport końcowy zawiera tabelę: ukończone (z commit/path/test), częściowo ukończone, blokery (z przyczyną), komendy lokalne, 3 następne wartościowe taski. **Nie markuj jako complete testów, których nie uruchomiono.**
