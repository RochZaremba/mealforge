"use client";
import { useEffect, useRef, useState } from "react";
import { api, currentAuthGeneration, errorMessage, type Household, type Session } from "@/lib/api";

type Preview = {
  title: string;
  ingredients: { literal_text: string; amount: null; unit: "unknown"; weight_state: "unknown" }[];
  instructions: { text: string; section_path: string[] }[];
  recipe_yield_raw: string[];
  persisted: false;
  planner_eligible: false;
};
function PreviewForm({ session, household, onClose }: { session: Session; household: Household; onClose: () => void }) {
  const [document, setDocument] = useState("");
  const [attested, setAttested] = useState(false);
  const [result, setResult] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || !household.capabilities.can_edit) return;
    setError(""); setResult(null);
    if (!attested) { setError("Potwierdź autorstwo całej przekazywanej receptury."); return; }
    const body = { document, rights_attestation: "i_am_author" };
    if (new TextEncoder().encode(document).byteLength > 12288 || new TextEncoder().encode(JSON.stringify(body)).byteLength > 16384) {
      setError("Dokument jest zbyt duży do jednego podglądu. Skróć go i spróbuj ponownie."); return;
    }
    const generation = currentAuthGeneration();
    setBusy(true);
    try {
      const preview = await api<Preview>(`households/${household.id}/recipe-imports/preview`, { method: "POST", session, body });
      if (mounted.current && generation === currentAuthGeneration()) setResult(preview);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration()) setError(errorMessage(problem));
    } finally { if (mounted.current && generation === currentAuthGeneration()) setBusy(false); }
  }
  return <section className="form-card" data-testid="jsonld-preview-form">
    <h3>Podgląd Twojej receptury JSON-LD</h3>
    <p className="note">Wklej sam JSON z jednym własnym przepisem: tytułem, listą składników i instrukcjami. Nie kopiuj chronionego tekstu. Podgląd nie zapisuje przepisu, nie pobiera stron ani zdjęć.</p>
    <form onSubmit={submit}><fieldset disabled={busy || !household.capabilities.can_edit}>
      <label htmlFor="jsonld-document">Własny dokument JSON-LD<textarea id="jsonld-document" rows={8} required value={document} spellCheck={false} onChange={(event) => { setDocument(event.target.value); setResult(null); setError(""); }} /></label>
      <label className="checkbox-label"><input type="checkbox" required checked={attested} onChange={(event) => { setAttested(event.target.checked); setResult(null); }} />Potwierdzam autorstwo całej przekazywanej receptury</label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button className="button" type="submit">{busy ? "Przygotowywanie podglądu…" : "Pokaż podgląd"}</button><button className="secondary-button" type="button" onClick={onClose}>Zamknij podgląd JSON-LD</button></div>
    </fieldset></form>
    {result && <div data-testid="jsonld-preview-result">
      <h3>{result.title}</h3><p className="form-warning">To niezapisany podgląd. Wartości odżywcze i alergeny są nieznane. Dokument nie jest dostępny dla planera.</p>
      <h4>Oryginalne zapisy składników</h4><p className="note">Nie rozpoznano ilości, jednostek ani stanu produktów. Zapis tekstowy nie potwierdza gramatury.</p>
      <ul>{result.ingredients.map((item, index) => <li key={index}>{item.literal_text}</li>)}</ul>
      <h4>Instrukcje</h4><ol>{result.instructions.map((step, index) => <li key={index}>{step.section_path.length > 0 && <strong>{step.section_path.join(" / ")}: </strong>}{step.text}</li>)}</ol>
      <h4>Deklaracja uzysku z dokumentu</h4>
      {result.recipe_yield_raw.length > 0 ? <ul>{result.recipe_yield_raw.map((value, index) => <li key={index}>{value}</li>)}</ul> : <p className="note">Nie podano.</p>}
      <p className="note">Nie zweryfikowano masy gotowej potrawy ani liczby osobowych porcji. Kalorie, makro, czasy, autor, licencja i deklaracje dietetyczne z dokumentu nie są potwierdzonymi danymi. Bezpieczeństwo przechowywania pozostaje nieznane.</p>
    </div>}
  </section>;
}
export function JsonldPreview({ session, household }: { session: Session; household: Household }) {
  const [opened, setOpened] = useState(false);
  if (!household.capabilities.can_edit) return null;
  return <section className="jsonld-preview-section"><div className="form-card"><h2>Podgląd własnego JSON-LD</h2><p className="note">Sprawdź dane receptury ze swojego dokumentu. Podgląd pozostaje prywatny i nie zapisuje przepisu.</p>
    {!opened && <button className="secondary-button" type="button" onClick={() => setOpened(true)}>Otwórz podgląd JSON-LD</button>}</div>
    {opened && <PreviewForm session={session} household={household} onClose={() => setOpened(false)} />}
  </section>;
}
