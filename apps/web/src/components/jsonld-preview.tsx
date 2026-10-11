"use client";
import { useEffect, useRef, useState } from "react";
import { api, currentAuthGeneration, errorMessage, type Household, type Session } from "@/lib/api";
import type { Recipe } from "@/lib/recipes";

type Preview = {
  title: string;
  ingredients: { literal_text: string; amount: null; unit: "unknown"; weight_state: "unknown" }[];
  instructions: { text: string; section_path: string[] }[];
  recipe_yield_raw: string[];
  persisted: false;
  planner_eligible: false;
};
function PreviewForm({ session, household, onClose, onImported }: { session: Session; household: Household; onClose: () => void; onImported: (recipe: Recipe) => void }) {
  const [document, setDocument] = useState("");
  const [attested, setAttested] = useState(false);
  const [result, setResult] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<Recipe | null>(null);
  const savedId = useRef<string | null>(null);
  const pending = useRef(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (pending.current || savedId.current || !household.capabilities.can_edit) return;
    setError(""); setResult(null);
    if (!attested) { setError("Potwierdź autorstwo całej przekazywanej receptury."); return; }
    const body = { document, rights_attestation: "i_am_author" };
    if (new TextEncoder().encode(document).byteLength > 12288 || new TextEncoder().encode(JSON.stringify(body)).byteLength > 16384) {
      setError("Dokument jest zbyt duży do jednego podglądu. Skróć go i spróbuj ponownie."); return;
    }
    const generation = currentAuthGeneration();
    pending.current = true;
    setBusy(true);
    try {
      const preview = await api<Preview>(`households/${household.id}/recipe-imports/preview`, { method: "POST", session, body });
      if (mounted.current && generation === currentAuthGeneration()) setResult(preview);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally { pending.current = false; if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  async function save() {
    if (pending.current || savedId.current || !result || !attested || !household.capabilities.can_edit) return;
    const generation = currentAuthGeneration();
    pending.current = true;
    setBusy(true); setSaving(true); setError("");
    try {
      const recipe = await api<Recipe>(`households/${household.id}/recipe-imports`, {
        method: "POST", session, body: { document, rights_attestation: "i_am_author" },
      });
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      savedId.current = recipe.id;
      setSaved(recipe);
      onImported(recipe);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally {
      pending.current = false;
      if (mounted.current && generation === currentAuthGeneration()) { setBusy(false); setSaving(false); }
    }
  }
  function startNext() {
    savedId.current = null;
    setDocument(""); setAttested(false); setResult(null); setSaved(null); setError("");
  }
  return <section className="form-card" data-testid="jsonld-preview-form">
    <h3>Podgląd Twojej receptury JSON-LD</h3>
    <p className="note">Wklej sam JSON z jednym własnym przepisem: tytułem, listą składników i instrukcjami. Nie kopiuj chronionego tekstu. Podgląd nie zapisuje przepisu, nie pobiera stron ani zdjęć. Zapis szkicu wymaga osobnego potwierdzenia.</p>
    <form onSubmit={submit}><fieldset disabled={busy || !!saved || !household.capabilities.can_edit}>
      <label htmlFor="jsonld-document">Własny dokument JSON-LD<textarea id="jsonld-document" rows={8} required value={document} spellCheck={false} onChange={(event) => { setDocument(event.target.value); setResult(null); setError(""); }} /></label>
      <label className="checkbox-label"><input type="checkbox" required checked={attested} onChange={(event) => { setAttested(event.target.checked); setResult(null); }} />Potwierdzam autorstwo całej przekazywanej receptury</label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="button" type="submit">{busy && !saving ? "Przygotowywanie podglądu…" : "Pokaż podgląd"}</button></div>
    </fieldset></form>
    {result && <div data-testid="jsonld-preview-result">
      <h3>{result.title}</h3><p className="form-warning">{saved ? "Zapisano prywatny szkic." : "To niezapisany podgląd."} Wartości odżywcze i alergeny są nieznane. Dokument nie jest dostępny dla planera.</p>
      <h4>Oryginalne zapisy składników</h4><p className="note">Nie rozpoznano ilości, jednostek ani stanu produktów. Zapis tekstowy nie potwierdza gramatury.</p>
      <ul>{result.ingredients.map((item, index) => <li key={index}>{item.literal_text}</li>)}</ul>
      <h4>Instrukcje</h4><ol>{result.instructions.map((step, index) => <li key={index}>{step.section_path.length > 0 && <strong>{step.section_path.join(" / ")}: </strong>}{step.text}</li>)}</ol>
      <h4>Deklaracja uzysku z dokumentu</h4>
      {result.recipe_yield_raw.length > 0 ? <ul>{result.recipe_yield_raw.map((value, index) => <li key={index}>{value}</li>)}</ul> : <p className="note">Nie podano.</p>}
      <p className="note">Nie zweryfikowano masy gotowej potrawy ani liczby osobowych porcji. Kalorie, makro, czasy, autor, licencja i deklaracje dietetyczne z dokumentu nie są potwierdzonymi danymi. Bezpieczeństwo przechowywania pozostaje nieznane.</p>
      {!saved && <><p className="note">Osobne kliknięcie zapisze szkic w tym gospodarstwie. Serwer ponownie sprawdzi dokument. Każdy zapis składnika może mieć do 160 znaków; cały szkic wraz z informacją o imporcie ma osobny limit rozmiaru. Dłuższe dane nie zostaną obcięte — zapis zwróci błąd, zachowując formularz.</p><button className="button" data-testid="jsonld-save" type="button" disabled={busy || !attested || !household.capabilities.can_edit} onClick={() => void save()}>{saving ? "Zapisywanie szkicu…" : "Zapisz szkic przepisu"}</button></>}
      {saved && <><p className="form-success" role="status" data-testid="jsonld-save-success">Szkic „{saved.title}” zapisany i potwierdzony przez serwer. Szczegóły są otwarte w katalogu przepisów.</p><button className="secondary-button" type="button" onClick={startNext}>Wklej kolejną recepturę</button></>}
    </div>}
    <div className="form-actions"><button className="secondary-button" type="button" disabled={busy} onClick={onClose}>Zamknij podgląd JSON-LD</button></div>
  </section>;
}
export function JsonldPreview({ session, household, onImported }: { session: Session; household: Household; onImported: (recipe: Recipe) => void }) {
  const [opened, setOpened] = useState(false);
  if (!household.capabilities.can_edit) return null;
  return <section className="jsonld-preview-section"><div className="form-card"><h2>Podgląd własnego JSON-LD</h2><p className="note">Sprawdź dane receptury ze swojego dokumentu. Sam podgląd nie zapisuje przepisu. Po sprawdzeniu możesz osobno zapisać prywatny szkic.</p>
    {!opened && <button className="secondary-button" type="button" onClick={() => setOpened(true)}>Otwórz podgląd JSON-LD</button>}</div>
    {opened && <PreviewForm session={session} household={household} onClose={() => setOpened(false)} onImported={onImported} />}
  </section>;
}
