"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, currentAuthGeneration, displayDecimal, errorMessage, type Household, type Session } from "@/lib/api";
import { stateLabels, unitLabels, type Ingredient, type Recipe, type RecipeHistory, type RecipePage } from "@/lib/recipes";
import { HouseholdSelector, useHousehold } from "./household-provider";
import { useSession } from "./session-provider";
import { RecipeLinks } from "./recipe-links";
import { JsonldPreview } from "./jsonld-preview";

function useMounted() {
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  return mounted;
}
function Feedback({ error, success }: { error?: string; success?: string }) {
  return <>{error && <p className="form-error" role="alert">{error}</p>}{success && <p className="form-success" role="status">{success}</p>}</>;
}
function DemoCreate({ session }: { session: Session }) {
  const { addConfirmedHousehold } = useHousehold();
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const mounted = useMounted();
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!confirmed) return;
    const generation = currentAuthGeneration();
    setBusy(true); setError(""); setSuccess("");
    try {
      const result = await api<{ household: Household }>("households/demo", { method: "POST", session, body: { confirmation: "create_separate_demo" } });
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      addConfirmedHousehold(result.household);
      setConfirmed(false);
      setSuccess("Utworzono osobne gospodarstwo demo. Dotychczasowe cele nie zostały zmienione.");
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  return <section className="form-card demo-card">
    <h2>Wypróbuj na osobnym demo</h2>
    <p className="section-description">Powstanie nowy dom z dwiema przykładowymi osobami, celami 2700/1600 kcal, pięcioma posiłkami i trzema oryginalnymi szkicami przepisów. Makro pozostaje nieznane. To przykład działania, nie zalecenie żywieniowe.</p>
    <p className="note">Twoje obecne gospodarstwo i cele pozostaną bez zmian.</p>
    <form data-testid="demo-create" onSubmit={submit}><fieldset disabled={busy}>
      <label className="checkbox-label"><input type="checkbox" required checked={confirmed} onChange={(e) => { setConfirmed(e.target.checked); setSuccess(""); }} />Rozumiem, że powstanie osobne gospodarstwo demo</label>
      <button type="submit" className="secondary-button" disabled={!confirmed}>{busy ? "Tworzenie demo…" : "Utwórz osobne demo"}</button>
    </fieldset></form>
    <Feedback error={error} success={success} />
  </section>;
}
function RecipeContent({ recipe, historical = false }: { recipe: Recipe; historical?: boolean }) {
  const origin = recipe.provenance.original_origin;
  const imported = recipe.provenance.import_origin;
  return <div className="recipe-content">
    <p className="form-warning">Szkic — wymaga sprawdzenia. Brak zweryfikowanych kalorii, makro i alergenów. Przepis nie jest jeszcze gotowy do planowania porcji.</p>
    <dl className="target-summary">
      <div><dt>Kalorie (kcal)</dt><dd data-testid={historical ? undefined : "recipe-kcal"}>Nieznane</dd></div>
      <div><dt>Białko (g)</dt><dd data-testid={historical ? undefined : "recipe-protein"}>Nieznane</dd></div>
      <div><dt>Węglowodany (g)</dt><dd data-testid={historical ? undefined : "recipe-carbs"}>Nieznane</dd></div>
      <div><dt>Tłuszcze (g)</dt><dd data-testid={historical ? undefined : "recipe-fat"}>Nieznane</dd></div>
      <div><dt>Alergeny</dt><dd data-testid={historical ? undefined : "recipe-allergens"}>Nieznane</dd></div>
      <div><dt>Masa po gotowaniu</dt><dd data-testid={historical ? undefined : "recipe-yield"}>Nieznana — wymaga zważenia</dd></div>
    </dl>
    <p className="note">Czas przygotowania, przechowywanie i ceny: nieznane. Nie zakładamy bezpieczeństwa dla alergików ani trwałości potrawy.</p>
    {recipe.servings !== null && <p className="note">Przepis zaprojektowano dla {recipe.servings} osób. To deklaracja autora, bez pomiaru masy i bez obliczonych porcji kalorycznych.</p>}
    <h3>Składniki</h3>
    <ul className="recipe-ingredients">{recipe.ingredients.map((item, index) => <li key={`ingredient-${index}`}>
      <strong>{item.name}</strong><span>{item.amount === null ? "Ilość nieznana" : displayDecimal(item.amount)}{item.amount !== null ? ` · ${unitLabels[item.unit]}` : ""} · {stateLabels[item.weight_state]}</span>
    </li>)}</ul>
    <p className="note">Ilości są zapisane zgodnie z deklaracją. Mililitrów i sztuk nie przeliczamy na gramy; suma składników nie jest zmierzoną masą gotowego dania.</p>
    <h3>Przygotowanie</h3>
    <ol className="recipe-steps">{recipe.instructions.map((step, index) => <li key={`step-${index}`}>{step}</li>)}</ol>
    <section className="recipe-origin" aria-label="Pochodzenie przepisu">
      <h3>Pochodzenie i prawa</h3>
      {recipe.provenance.source_id === "original_fixture" ? <p>Oryginalny tekst MealForge · CC0-1.0, wyłącznie tekst przepisu.</p> : <p>Własny wkład: {recipe.provenance.author}. Treść prywatna; licencja nieznana.</p>}
      {recipe.provenance.attribution && <p className="note">{recipe.provenance.attribution}</p>}
      {origin && <p className="note">Baza oryginalnego tekstu: {origin.author} · {origin.license}, wyłącznie tekst przepisu. {origin.attribution} Własne zmiany pozostają prywatne z nieznaną licencją.</p>}
      {imported && <>
        <p className="note" data-testid="jsonld-current-source">{recipe.provenance.source_mode === "user_supplied_jsonld" ? "Ta wersja jest szkicem z własnego dokumentu JSON-LD." : "Ta wersja zawiera ręczne zmiany. Oryginalne dane importu poniżej pozostają bez zmian."}</p>
        <details data-testid="jsonld-import-origin" className="jsonld-import-origin">
          <summary>Oryginalne dane importu JSON-LD</summary>
          <p className="note">To zapis oryginalnego zgłoszenia, a nie potwierdzenie aktualnych ilości lub instrukcji. Skrót identyfikuje dokument; nie potwierdza praw autorskich ani wartości odżywczych.</p>
          <p className="note">Identyfikator dokumentu (SHA-256): <code data-testid="jsonld-source-sha256">{imported.source_sha256}</code></p>
          <h4>Oryginalne zapisy składników</h4>
          <ul>{imported.ingredients.map((item, index) => <li key={`import-ingredient-${index}`}>{item}</li>)}</ul>
          <h4>Oryginalne instrukcje i sekcje</h4>
          <ol>{imported.instructions.map((step, index) => <li key={`import-step-${index}`}>{step.section_path.length > 0 && <strong>{step.section_path.join(" / ")}: </strong>}{step.text}</li>)}</ol>
          <h4>Deklaracja uzysku z oryginalnego dokumentu</h4>
          {imported.recipe_yield_raw.length ? <ul>{imported.recipe_yield_raw.map((item, index) => <li key={`import-yield-${index}`}>{item}</li>)}</ul> : <p className="note">Nie podano.</p>}
          <p className="note">To niezweryfikowany tekst. Nie określa zmierzonej masy dania, liczby osobowych porcji ani kaloryczności.</p>
        </details>
      </>}
    </section>
    {recipe.warnings.map((warning, index) => <p className="note" key={`warning-${warning.code}-${index}`}>{warning.message}</p>)}
  </div>;
}
type IngredientDraft = Ingredient & { key: number; amountText: string };
type StepDraft = { key: number; text: string };
function RecipeForm({ session, householdId, recipe, onSaved, onCancel }: { session: Session; householdId: string; recipe?: Recipe; onSaved: (recipe: Recipe) => void; onCancel: () => void }) {
  const [title, setTitle] = useState(recipe?.title ?? "");
  const [ingredients, setIngredients] = useState<IngredientDraft[]>(() => (recipe?.ingredients ?? [{ name: "", amount: null, unit: "unknown", weight_state: "unknown" }]).map((item, index) => ({ ...item, key: index, amountText: item.amount ?? "" })));
  const [steps, setSteps] = useState<StepDraft[]>(() => (recipe?.instructions ?? [""]).map((text, index) => ({ key: index, text })));
  const ingredientKey = useRef(ingredients.length);
  const stepKey = useRef(steps.length);
  const [attested, setAttested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const mounted = useMounted();
  function updateIngredient(index: number, value: Partial<IngredientDraft>) { setIngredients((items) => items.map((item, i) => i === index ? { ...item, ...value } : item)); }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const generation = currentAuthGeneration();
    setError("");
    const payload = { title: title.trim(), ingredients: ingredients.map((item) => ({ name: item.name.trim(), amount: item.amountText.trim() === "" ? null : item.amountText.trim().replace(",", "."), unit: item.unit, weight_state: item.weight_state })), instructions: steps.map((item) => item.text.trim()), rights_attestation: "i_am_author", ...(recipe ? { expected_version: recipe.version } : {}) };
    if (!attested || !payload.title || payload.ingredients.some((item) => !item.name) || payload.instructions.some((item) => !item)) { setError("Uzupełnij nazwę, składniki i kroki oraz potwierdź autorstwo własnego wkładu."); return; }
    if (payload.ingredients.some((item) => item.amount !== null && !/^(?!0(?:\.0{1,3})?$)(?:0|[1-9]\d{0,5})(?:\.\d{1,3})?$/.test(item.amount))) { setError("Ilość powinna być dodatnią liczbą z najwyżej trzema miejscami po przecinku. Brak ilości pozostaw pusty."); return; }
    if (new TextEncoder().encode(JSON.stringify(payload)).byteLength > 16384) { setError("Przepis jest zbyt długi do jednego zapisu. Skróć tekst lub liczbę składników i spróbuj ponownie. Formularz zachowuje Twoje zmiany."); return; }
    setBusy(true);
    try {
      const value = await api<Recipe>(`households/${householdId}/recipes${recipe ? `/${recipe.id}` : ""}`, { method: recipe ? "PUT" : "POST", session, body: payload });
      if (mounted.current && generation === currentAuthGeneration()) onSaved(value);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) { setError(errorMessage(problem)); setConflict(problem instanceof ApiError && problem.status === 409); }
    } finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  return <section className="form-card" aria-label={recipe ? "Edycja przepisu" : "Nowy własny przepis"}>
    <h2>{recipe ? "Edytuj własny wkład" : "Dodaj własny przepis"}</h2>
    {recipe?.provenance.source_id === "original_fixture" || recipe?.provenance.original_origin ? <p className="note">Oryginalna baza MealForge zachowa autorstwo i CC0. Potwierdzasz autorstwo tylko własnych zmian; nie nadajemy im automatycznie licencji CC0.</p> : <p className="note">Wprowadź własny tekst. Przepis pozostanie prywatnym szkicem z nieznaną licencją.</p>}
    <form data-testid="recipe-form" onSubmit={submit}><fieldset disabled={busy}>
      <label htmlFor="recipe-title">Nazwa przepisu<input id="recipe-title" required maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
      <h3>Składniki</h3>
      {ingredients.map((item, index) => <div className="recipe-ingredient-editor" key={`ingredient-form-${item.key}`}>
        <label htmlFor={`ingredient-name-${item.key}`}>Składnik {index + 1}<input id={`ingredient-name-${item.key}`} required maxLength={160} value={item.name} onChange={(e) => updateIngredient(index, { name: e.target.value })} /></label>
        <label htmlFor={`ingredient-amount-${item.key}`}>Ilość składnika {index + 1}<input id={`ingredient-amount-${item.key}`} inputMode="decimal" placeholder="Nieznana" maxLength={10} value={item.amountText} onChange={(e) => updateIngredient(index, { amountText: e.target.value })} /></label>
        <label htmlFor={`ingredient-unit-${item.key}`}>Jednostka składnika {index + 1}<select id={`ingredient-unit-${item.key}`} value={item.unit} onChange={(e) => updateIngredient(index, { unit: e.target.value as Ingredient["unit"] })}>{Object.entries(unitLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <label htmlFor={`ingredient-state-${item.key}`}>Stan składnika {index + 1}<select id={`ingredient-state-${item.key}`} value={item.weight_state} onChange={(e) => updateIngredient(index, { weight_state: e.target.value as Ingredient["weight_state"] })}>{Object.entries(stateLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <button type="button" className="secondary-button" disabled={ingredients.length <= 1} onClick={() => setIngredients((items) => items.filter((_, i) => i !== index))}>Usuń składnik {index + 1}</button>
      </div>)}
      <button type="button" className="secondary-button" disabled={ingredients.length >= 40} onClick={() => setIngredients((items) => [...items, { key: ingredientKey.current++, name: "", amount: null, amountText: "", unit: "unknown", weight_state: "unknown" }])}>Dodaj składnik</button>
      <h3>Przygotowanie</h3>
      {steps.map((step, index) => <div className="recipe-step-editor" key={`step-form-${step.key}`}>
        <label htmlFor={`recipe-step-${step.key}`}>Krok {index + 1}<textarea id={`recipe-step-${step.key}`} required maxLength={500} rows={3} value={step.text} onChange={(e) => setSteps((items) => items.map((item, i) => i === index ? { ...item, text: e.target.value } : item))} /></label>
        <button type="button" className="secondary-button" disabled={steps.length <= 1} onClick={() => setSteps((items) => items.filter((_, i) => i !== index))}>Usuń krok {index + 1}</button>
      </div>)}
      <button type="button" className="secondary-button" disabled={steps.length >= 30} onClick={() => setSteps((items) => [...items, { key: stepKey.current++, text: "" }])}>Dodaj krok</button>
      <label className="checkbox-label"><input type="checkbox" required checked={attested} onChange={(e) => setAttested(e.target.checked)} />Potwierdzam autorstwo własnego wkładu</label>
      <Feedback error={error} />
      {conflict && <p className="form-warning">Ktoś zapisał nowszą wersję. Twoje zmiany są nadal w formularzu. Zamknij formularz i odśwież przepis, aby porównać dane przed kolejną edycją.</p>}
      <div className="form-actions"><button className="button" type="submit" disabled={conflict}>{busy ? "Zapisywanie…" : recipe ? "Zapisz nową wersję" : "Zapisz przepis"}</button><button type="button" className="secondary-button" onClick={onCancel}>Zamknij formularz</button></div>
    </fieldset></form>
  </section>;
}
function RecipeDetail({ session, household, recipe: initialRecipe, onClose, onSaved }: { session: Session; household: Household; recipe: Recipe; onClose: () => void; onSaved: () => void }) {
  const [recipe, setRecipe] = useState(initialRecipe);
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState<RecipeHistory | null>(null);
  const [before, setBefore] = useState<number | null>(null);
  const [historyPages, setHistoryPages] = useState<(number | null)[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const { refreshHouseholds } = useHousehold();
  const mounted = useMounted();
  async function failure(problem: unknown) {
    setError(errorMessage(problem));
    if (problem instanceof ApiError && (problem.status === 403 || problem.status === 404)) {
      setHistory(null); setEditing(false); onClose();
      await refreshHouseholds().catch(() => {});
    }
  }
  async function loadHistory(cursor: number | null, previousPages: (number | null)[]) {
    const generation = currentAuthGeneration();
    setBusy(true); setError(""); setHistory(null);
    try {
      const result = await api<RecipeHistory>(`households/${household.id}/recipes/${recipe.id}/history?limit=2${cursor === null ? "" : `&before_version=${cursor}`}`);
      if (mounted.current && generation === currentAuthGeneration()) { setHistory(result); setBefore(cursor); setHistoryPages(previousPages); }
    } catch (problem) { if (mounted.current && generation === currentAuthGeneration()) await failure(problem); }
    finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  async function refreshRecipe() {
    const generation = currentAuthGeneration();
    setBusy(true); setError(""); setSuccess("");
    try {
      const result = await api<Recipe>(`households/${household.id}/recipes/${recipe.id}`);
      if (mounted.current && generation === currentAuthGeneration()) { setRecipe(result); setHistory(null); }
    } catch (problem) { if (mounted.current && generation === currentAuthGeneration()) await failure(problem); }
    finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  return <section className="form-card recipe-detail" data-testid="recipe-detail" data-recipe-id={recipe.id}>
    <div className="card-heading"><div><h2>{recipe.title}</h2><p className="note">Wersja {recipe.version}</p></div><button className="secondary-button" type="button" disabled={busy} onClick={onClose}>Zamknij przepis</button></div>
    <Feedback error={error} success={success} />
    {editing && household.capabilities.can_edit ? <RecipeForm key={`recipe-form-${recipe.version_id}`} session={session} householdId={household.id} recipe={recipe} onCancel={() => setEditing(false)} onSaved={(result) => { setRecipe(result); setEditing(false); setHistory(null); setSuccess("Nowa wersja przepisu zapisana i potwierdzona przez serwer."); onSaved(); }} /> : <>
      <RecipeContent recipe={recipe} />
      <div className="form-actions">
        {household.capabilities.can_edit && <button type="button" className="button" disabled={busy} onClick={() => { setEditing(true); setSuccess(""); }}>Edytuj przepis</button>}
        <button className="secondary-button" type="button" disabled={busy} onClick={() => void refreshRecipe()}>Odśwież przepis</button>
        <button className="secondary-button" type="button" disabled={busy} onClick={() => void loadHistory(null, [])}>Historia przepisu</button>
      </div>
    </>}
    {busy && <p role="status">Pobieranie przepisu…</p>}
    {history && <section className="history-list recipe-history" data-testid="recipe-history">
      <h3>Historia przepisu</h3>
      {history.history.map((item) => <details key={`recipe-version-${item.version_id}`} data-version={item.version}><summary>Wersja {item.version} · {item.title}</summary><RecipeContent recipe={item} historical /></details>)}
      <div className="pagination">
        <button type="button" className="secondary-button" disabled={busy || historyPages.length === 0} onClick={() => { const pages = historyPages.slice(0, -1); void loadHistory(historyPages.at(-1) ?? null, pages); }}>Nowsze wersje</button>
        <button type="button" data-testid="recipe-history-next" className="secondary-button" disabled={busy || history.next_before_version === null} onClick={() => void loadHistory(history.next_before_version, [...historyPages, before])}>Starsze wersje</button>
      </div>
    </section>}
  </section>;
}
function PrivateCatalog({ session, household }: { session: Session; household: Household }) {
  const [page, setPage] = useState<RecipePage | null>(null);
  const [after, setAfter] = useState<string | null>(null);
  const [pages, setPages] = useState<(string | null)[]>([]);
  const [limit, setLimit] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [creating, setCreating] = useState(false);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [reload, setReload] = useState(0);
  const { refreshHouseholds } = useHousehold();
  const mounted = useMounted();
  const detailRequest = useRef(0);
  useEffect(() => {
    let active = true;
    const generation = currentAuthGeneration();
    api<RecipePage>(`households/${household.id}/recipes?limit=${limit}${after === null ? "" : `&after=${encodeURIComponent(after)}`}`)
      .then((result) => { if (active && generation === currentAuthGeneration()) setPage(result); })
      .catch((problem) => {
        if (!active || generation !== currentAuthGeneration()) return;
        setPage(null); setError(errorMessage(problem));
        if (problem instanceof ApiError && (problem.status === 403 || problem.status === 404)) { setRecipe(null); setCreating(false); void refreshHouseholds().catch(() => {}); }
      });
    return () => { active = false; };
  }, [household.id, after, limit, reload, refreshHouseholds]);
  async function open(id: string) {
    const generation = currentAuthGeneration();
    const request = ++detailRequest.current;
    setBusy(true); setError(""); setSuccess(""); setRecipe(null); setCreating(false);
    try {
      const value = await api<Recipe>(`households/${household.id}/recipes/${id}`);
      if (mounted.current && generation === currentAuthGeneration() && request === detailRequest.current) setRecipe(value);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration() && request === detailRequest.current) {
        setError(errorMessage(problem));
        if (problem instanceof ApiError && (problem.status === 403 || problem.status === 404)) await refreshHouseholds().catch(() => {});
      }
    } finally { if (mounted.current && generation === currentAuthGeneration() && request === detailRequest.current) setBusy(false); }
  }
  function invalidateDetailRequest() { detailRequest.current += 1; setBusy(false); }
  function move(next: string | null, previousPages: (string | null)[]) { invalidateDetailRequest(); setPage(null); setAfter(next); setPages(previousPages); setRecipe(null); setCreating(false); setSuccess(""); setError(""); }
  function refreshList() { setError(""); setPage(null); setReload((value) => value + 1); }
  return <div className="household-stack">
    <section className="form-card">
      <div className="card-heading"><h2>Przepisy w Waszej kuchni</h2><div className="form-actions">
        {household.capabilities.can_edit && <button className="button" type="button" disabled={busy} onClick={() => { invalidateDetailRequest(); setCreating(true); setRecipe(null); setError(""); setSuccess(""); }}>Dodaj własny przepis</button>}
        <button className="secondary-button" type="button" disabled={busy} onClick={refreshList}>Odśwież katalog</button>
      </div></div>
      {!household.capabilities.can_edit && <p className="note">Masz dostęp do podglądu. Przepisy edytuje właściciel lub edytor.</p>}
      <p className="note">Własne teksty i oryginalne szkice. Treści z innych stron nie są pobierane.</p>
      <Feedback error={error} success={success} />
      <label className="page-size" htmlFor="recipes-page-size">Przepisy na stronie<select id="recipes-page-size" disabled={busy} value={limit} onChange={(e) => { setLimit(Number(e.target.value)); move(null, []); }}>{[2, 10, 20].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      {busy && <p role="status">Pobieranie szczegółów…</p>}
      {!page && !error && <p role="status">Pobieranie przepisów…</p>}
      {page && <>
        {page.recipes.length === 0 && <p className="section-description">Nie ma jeszcze przepisów. Dodaj własny tekst albo utwórz osobne demo.</p>}
        <div className="recipe-list" data-testid="recipe-list">{page.recipes.map((item) => <article className="recipe-card" key={`recipe-card-${item.id}`} data-testid="recipe-card" data-recipe-id={item.id}>
          <span className="tag">Szkic — wymaga sprawdzenia</span><h3>{item.title}</h3><p className="note">Wersja {item.version} · kalorie i makro nieznane</p>
          <button className="secondary-button" type="button" disabled={busy} onClick={() => void open(item.id)} aria-label={`Otwórz ${item.title}`}>Otwórz przepis</button>
        </article>)}</div>
        <div className="pagination"><button className="secondary-button" type="button" disabled={busy || pages.length === 0} onClick={() => move(pages.at(-1) ?? null, pages.slice(0, -1))}>Poprzednia strona</button><button data-testid="recipe-list-next" className="secondary-button" type="button" disabled={busy || page.next_cursor === null} onClick={() => move(page.next_cursor, [...pages, after])}>Następna strona</button></div>
      </>}
    </section>
    {creating && household.capabilities.can_edit && <RecipeForm key="recipe-create-form" session={session} householdId={household.id} onCancel={() => setCreating(false)} onSaved={(result) => { invalidateDetailRequest(); setCreating(false); setRecipe(result); setSuccess("Przepis zapisany i potwierdzony przez serwer."); refreshList(); }} />}
    {recipe && <RecipeDetail key={`recipe-detail-${recipe.id}`} session={session} household={household} recipe={recipe} onClose={() => { invalidateDetailRequest(); setRecipe(null); }} onSaved={refreshList} />}
    <JsonldPreview key={`jsonld-${session.user.id}-${household.id}`} household={household} session={session} onImported={(imported) => { invalidateDetailRequest(); setCreating(false); setRecipe(imported); setSuccess("Szkic z własnego JSON-LD zapisany i potwierdzony przez serwer."); refreshList(); }} />
  </div>;
}
export function RecipesScreen() {
  const { session, loading: sessionLoading } = useSession();
  const { household, loading, error, refreshHouseholds } = useHousehold();
  return <>
    <div className="page-heading"><p className="eyebrow">WASZE WŁASNE POMYSŁY</p><h1>Przepisy</h1><p>Zapisuj własne składniki i sposób przygotowania.</p></div>
    {sessionLoading ? <p role="status">Sprawdzanie sesji…</p> : !session ? <section className="form-card"><h2>Prywatny katalog Waszej kuchni</h2><p>Zaloguj się, aby zobaczyć lub zapisać przepisy gospodarstwa.</p><Link className="button" href="/household">Przejdź do logowania</Link></section> : <>
      <HouseholdSelector />
      {loading && <p role="status">Sprawdzanie gospodarstwa…</p>}
      {error && <section className="form-card"><Feedback error={error} /><button className="secondary-button" type="button" onClick={() => void refreshHouseholds().catch(() => {})}>Sprawdź gospodarstwa ponownie</button></section>}
      {household ? <div hidden={loading || !!error} inert={loading || !!error}><PrivateCatalog key={`catalog-${session.user.id}-${household.id}`} household={household} session={session} /><RecipeLinks key={`recipe-links-${session.user.id}-${household.id}`} household={household} session={session} /></div> : !loading && !error && <section className="form-card"><h2>Wybierz swoją kuchnię</h2><p>Utwórz gospodarstwo albo zacznij od osobnego demo.</p><Link className="button" href="/household">Ustaw gospodarstwo</Link></section>}
      <DemoCreate key={`demo-${session.user.id}`} session={session} />
    </>}
  </>;
}
