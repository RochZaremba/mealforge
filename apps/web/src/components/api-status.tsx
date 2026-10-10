"use client";
import { useEffect, useState } from "react";
type Check = { state: "loading" | "success" | "failure"; message: string };
const pending: Check = { state: "loading", message: "Sprawdzanie…" };
async function checkService(path: string, expected: string): Promise<Check> {
 try {
   const response = await fetch(`/api/${path}`, { cache: "no-store", signal: AbortSignal.timeout(6000) });
   const payload: unknown = await response.json();
   if (response.ok && typeof payload === "object" && payload !== null && "status" in payload && payload.status === expected) return { state: "success", message: expected === "ok" ? "API odpowiada · ok" : "Baza danych gotowa · ready" };
   return { state: "failure", message: path === "ready" ? "Usługa niedostępna lub nie jest jeszcze gotowa" : "API niedostępne — nie udało się potwierdzić połączenia" };
 } catch { return { state: "failure", message: "Brak połączenia z usługą" }; }
}
export function ApiStatus() {
 const [health, setHealth] = useState<Check>(pending);
 const [ready, setReady] = useState<Check>(pending);
 const [attempt, setAttempt] = useState(0);
 useEffect(() => {
   let active = true;
   Promise.all([checkService("health", "ok"), checkService("ready", "ready")]).then(([healthResult, readyResult]) => { if (active) { setHealth(healthResult); setReady(readyResult); } });
   return () => { active = false; };
 }, [attempt]);
 const busy = health.state === "loading" || ready.state === "loading";
 return <section className="status-card" aria-labelledby="connection-title"><h2 id="connection-title">Połączenie z usługami</h2><p>Wynik bieżącego sprawdzenia API i bazy danych.</p><dl className="status-list" aria-live="polite"><div><dt>API</dt><dd data-testid="api-health" data-state={health.state}><span className={`status-dot ${health.state}`} aria-hidden="true"/>{health.message}</dd></div><div><dt>Gotowość</dt><dd data-testid="api-ready" data-state={ready.state}><span className={`status-dot ${ready.state}`} aria-hidden="true"/>{ready.message}</dd></div></dl><button className="button" disabled={busy} onClick={() => { setHealth(pending); setReady(pending); setAttempt((value) => value + 1); }}>{busy ? "Sprawdzanie…" : "Sprawdź ponownie"}</button><p className="note">Gotowość usług nie oznacza ukończenia funkcji planowania. To sprawdzenie nie pobiera danych domowników.</p></section>;
}
