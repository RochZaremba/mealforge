"use client";
import { useEffect, useRef, useState } from "react";
import { api, currentAuthGeneration, errorMessage, type Household, type Session } from "@/lib/api";
import { safeOpeningUrl, type RecipeLink, type RecipeLinkPage, type RecipeLinkSummary } from "@/lib/recipe-links";

function useMounted() {
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  return mounted;
}
function Feedback({ error, success }: { error?: string; success?: string }) {
  return <>{error && <p className="form-error" role="alert">{error}</p>}{success && <p className="form-success" role="status">{success}</p>}</>;
}
function LinkUnknowns() {
  return <p className="form-warning" data-testid="recipe-link-unknown">Wartości odżywcze i alergeny nieznane. Link nie jest dostępny dla planera.</p>;
}
function LinkDetail({ link, onClose }: { link: RecipeLink; onClose: () => void }) {
  const href = safeOpeningUrl(link.source_url);
  return <section className="form-card recipe-link-detail" data-testid="recipe-link-detail" data-link-id={link.id}>
    <div className="card-heading"><div><span className="tag">Tylko link</span><h3>{link.user_title}</h3></div><button className="secondary-button" type="button" onClick={onClose}>Zamknij szczegóły linku</button></div>
    <LinkUnknowns />
    <p className="note" data-testid="recipe-link-source">{link.source_id ? `Rozpoznane źródło: ${link.source_id}` : "Nieznane źródło"} · {link.host}</p>
    <p className="note">Prawa do treści źródłowej i jej licencja są nieznane. Rozpoznanie domeny nie oznacza zgody na import. Zapisano tylko adres, Twój tytuł i własną notatkę.</p>
    <h4>Twoja własna notatka</h4>
    <p data-testid="recipe-link-note" className="recipe-link-note">{link.own_note === null ? "Nie dodano notatki." : link.own_note}</p>
    <p className="note">Tytuł i notatka są Twoim tekstem, bez weryfikacji wartości odżywczych, alergenów i bezpieczeństwa przechowywania. Nie są danymi o przepisie.</p>
    <p className="recipe-link-url" data-testid="recipe-link-url">{link.source_url}</p>
    {href ? <a className="button" href={href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Otwórz stronę źródłową</a> : <p className="form-error" role="alert">Nie można bezpiecznie otworzyć zapisanego adresu.</p>}
    <p className="note">Strona zewnętrzna otworzy się w nowej karcie po kliknięciu. MealForge nie pobiera jej tekstu, zdjęć ani podglądu.</p>
  </section>;
}
function LinkForm({ session, household, onSaved, onCancel }: { session: Session; household: Household; onSaved: (link: RecipeLink) => void; onCancel: () => void }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [attested, setAttested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mounted = useMounted();
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!household.capabilities.can_edit || busy) return;
    const generation = currentAuthGeneration();
    setError("");
    const body = { user_title: title.trim(), source_url: url.trim(), own_note: note.trim() || null, own_contribution_attestation: "i_am_author_of_label_and_note" };
    if (!attested || !body.user_title) { setError("Dodaj własny tytuł i potwierdź autorstwo tytułu oraz notatki."); return; }
    if (new TextEncoder().encode(body.source_url).byteLength > 2048) { setError("Adres jest zbyt długi. Możesz zapisać do 2048 bajtów adresu."); return; }
    if (new TextEncoder().encode(JSON.stringify(body)).byteLength > 16384) { setError("Dane są zbyt długie do jednego zapisu. Skróć własny tekst i spróbuj ponownie."); return; }
    setBusy(true);
    try {
      const result = await api<RecipeLink>(`households/${household.id}/recipe-links`, { method: "POST", session, body });
      if (mounted.current && generation === currentAuthGeneration()) onSaved(result);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally {
      if (mounted.current && generation === currentAuthGeneration()) setBusy(false);
    }
  }
  return <section className="form-card">
    <h3>Zapisz sam adres i własny tekst</h3>
    <p className="note">Nadaj własny tytuł. Nie kopiuj chronionego tekstu ani zdjęć źródłowej strony. Potwierdzenie dotyczy tylko Twojego tytułu i notatki.</p>
    <form data-testid="recipe-link-form" onSubmit={submit}><fieldset disabled={busy || !household.capabilities.can_edit}>
      <label htmlFor="recipe-link-title">Własny tytuł linku<input id="recipe-link-title" required maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
      <label htmlFor="recipe-link-address">Adres strony (HTTPS)<input id="recipe-link-address" required type="url" inputMode="url" autoCapitalize="none" autoComplete="off" spellCheck={false} value={url} onChange={(e) => setUrl(e.target.value)} /></label>
      <label htmlFor="recipe-link-own-note">Własna notatka (opcjonalnie)<textarea id="recipe-link-own-note" maxLength={2000} rows={4} value={note} onChange={(e) => setNote(e.target.value)} /></label>
      <label className="checkbox-label"><input type="checkbox" required checked={attested} onChange={(e) => setAttested(e.target.checked)} />Potwierdzam autorstwo własnego tytułu i notatki</label>
      <Feedback error={error} />
      <div className="form-actions"><button className="button" type="submit">{busy ? "Zapisywanie linku…" : "Zapisz link"}</button><button type="button" className="secondary-button" onClick={onCancel}>Zamknij formularz linku</button></div>
    </fieldset></form>
  </section>;
}
export function RecipeLinks({ session, household }: { session: Session; household: Household }) {
  const [page, setPage] = useState<RecipeLinkPage | null>(null);
  const [after, setAfter] = useState<string | null>(null);
  const [previous, setPrevious] = useState<(string | null)[]>([]);
  const [limit, setLimit] = useState(10);
  const [reload, setReload] = useState(0);
  const [creating, setCreating] = useState(false);
  const [detail, setDetail] = useState<RecipeLink | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const mounted = useMounted();
  useEffect(() => {
    let active = true;
    const generation = currentAuthGeneration();
    api<RecipeLinkPage>(`households/${household.id}/recipe-links?limit=${limit}${after === null ? "" : `&after=${encodeURIComponent(after)}`}`)
      .then((result) => { if (active && generation === currentAuthGeneration()) setPage(result); })
      .catch((problem) => {
        if (active && generation === currentAuthGeneration()) { setPage(null); setError(errorMessage(problem)); }
      });
    return () => { active = false; };
  }, [household.id, limit, after, reload]);
  function refreshList() { setPage(null); setError(""); setReload((value) => value + 1); }
  function move(cursor: string | null, pages: (string | null)[]) {
    setPage(null); setAfter(cursor); setPrevious(pages); setDetail(null); setSuccess(""); setError("");
  }
  async function open(link: RecipeLinkSummary) {
    const generation = currentAuthGeneration();
    setBusy(true); setDetail(null); setError(""); setSuccess("");
    try {
      const result = await api<RecipeLink>(`households/${household.id}/recipe-links/${link.id}`);
      if (mounted.current && generation === currentAuthGeneration()) setDetail(result);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  return <section className="recipe-links-section" data-testid="recipe-links" aria-labelledby="recipe-links-heading">
    <div className="form-card">
      <div className="card-heading"><h2 id="recipe-links-heading">Zapisane linki</h2><div className="form-actions">
        {household.capabilities.can_edit && <button className="button" type="button" disabled={busy} onClick={() => { setCreating(true); setDetail(null); setError(""); setSuccess(""); }}>Dodaj link</button>}
        <button className="secondary-button" type="button" disabled={busy} onClick={refreshList}>Odśwież linki</button>
      </div></div>
      <p className="section-description">Własne tytuły i notatki do źródłowych stron. Zapisanie linku nie importuje przepisu.</p>
      <LinkUnknowns />
      {!household.capabilities.can_edit && <p className="note">Masz dostęp do podglądu. Linki zapisuje właściciel lub edytor.</p>}
      <Feedback error={error} success={success} />
      <label className="page-size" htmlFor="recipe-links-page-size">Linki na stronie<select id="recipe-links-page-size" value={limit} disabled={busy} onChange={(e) => { setLimit(Number(e.target.value)); move(null, []); }}>{[2, 10, 20].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      {!page && !error && <p role="status">Pobieranie zapisanych linków…</p>}
      {busy && <p role="status">Pobieranie szczegółów linku…</p>}
      {page && <>
        {page.recipe_links.length === 0 && <p className="note">Nie zapisano jeszcze linków.</p>}
        <div className="recipe-list" data-testid="recipe-link-list">{page.recipe_links.map((link) => <article className="recipe-card" data-testid="recipe-link-card" data-link-id={link.id} key={`recipe-link-card-${link.id}`}>
          <span className="tag">Tylko link</span><h3>{link.user_title}</h3><p className="note">{link.host} · {link.source_id ? "Źródło rozpoznane, prawa nieznane" : "Nieznane źródło"}</p>
          <button className="secondary-button" type="button" disabled={busy} aria-label={`Szczegóły linku ${link.user_title}`} onClick={() => void open(link)}>Zobacz szczegóły</button>
        </article>)}</div>
        <div className="pagination"><button className="secondary-button" type="button" disabled={busy || previous.length === 0} onClick={() => move(previous.at(-1) ?? null, previous.slice(0, -1))}>Poprzednia strona linków</button><button className="secondary-button" type="button" data-testid="recipe-link-next" disabled={busy || page.next_cursor === null} onClick={() => move(page.next_cursor, [...previous, after])}>Następna strona linków</button></div>
      </>}
    </div>
    {creating && household.capabilities.can_edit && <LinkForm key="recipe-link-create" session={session} household={household} onCancel={() => setCreating(false)} onSaved={(link) => { setCreating(false); setDetail(link); setSuccess("Link zapisany i potwierdzony przez serwer. Treść strony nie została pobrana."); refreshList(); }} />}
    {detail && <LinkDetail key={`recipe-link-detail-${detail.id}`} link={detail} onClose={() => setDetail(null)} />}
  </section>;
}
