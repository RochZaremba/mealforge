"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, currentAuthGeneration, errorMessage, type Household } from "@/lib/api";
import { useSession } from "./session-provider";

type HouseholdContextValue = {
  households: Household[];
  selectedId: string;
  household: Household | null;
  loading: boolean;
  error: string;
  selectHousehold: (id: string) => void;
  refreshHouseholds: (preferredId?: string) => Promise<Household[]>;
  confirmHouseholds: (items: Household[], preferredId?: string) => void;
  addConfirmedHousehold: (item: Household) => void;
};
const HouseholdContext = createContext<HouseholdContextValue | null>(null);
function PrivateHouseholdProvider({ children }: { children: React.ReactNode }) {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const loadRevision = useRef(0);
  const mounted = useRef(false);
  const applyHouseholds = useCallback((items: Household[], preferredId?: string) => {
    setHouseholds(items);
    setSelectedId((current) => items.some((h) => h.id === (preferredId ?? current))
      ? (preferredId ?? current) : (items[0]?.id ?? ""));
    setError("");
  }, []);
  const confirmHouseholds = useCallback((items: Household[], preferredId?: string) => {
    loadRevision.current += 1;
    applyHouseholds(items, preferredId);
    setLoading(false);
  }, [applyHouseholds]);
  const refreshHouseholds = useCallback(async (preferredId?: string) => {
    const revision = ++loadRevision.current;
    const generation = currentAuthGeneration();
    setLoading(true);
    setError("");
    try {
      const result = await api<{ households: Household[] }>("households");
      if (mounted.current && revision === loadRevision.current && generation === currentAuthGeneration())
        applyHouseholds(result.households, preferredId);
      return result.households;
    } catch (problem) {
      if (mounted.current && revision === loadRevision.current && generation === currentAuthGeneration()) {
        setError(errorMessage(problem));
      }
      throw problem;
    } finally {
      if (mounted.current && revision === loadRevision.current && generation === currentAuthGeneration()) setLoading(false);
    }
  }, [applyHouseholds]);
  useEffect(() => {
    let active = true;
    mounted.current = true;
    void Promise.resolve().then(() => { if (active) return refreshHouseholds(); }).catch(() => {});
    const focus = () => { void refreshHouseholds().catch(() => {}); };
    const denied = (event: Event) => {
      const id = (event as CustomEvent<{ householdId: string }>).detail?.householdId;
      if (!id) return;
      loadRevision.current += 1;
      setHouseholds((items) => items.filter((item) => item.id !== id));
      setSelectedId((current) => current === id ? "" : current);
      void refreshHouseholds().catch(() => {});
    };
    window.addEventListener("focus", focus);
    window.addEventListener("mealforge-household-denied", denied);
    return () => {
      active = false;
      mounted.current = false;
      loadRevision.current += 1;
      window.removeEventListener("focus", focus);
      window.removeEventListener("mealforge-household-denied", denied);
    };
  }, [refreshHouseholds]);
  const selectHousehold = useCallback((id: string) => {
    if (households.some((item) => item.id === id)) setSelectedId(id);
  }, [households]);
  const addConfirmedHousehold = useCallback((item: Household) => {
    loadRevision.current += 1;
    setHouseholds((items) => [...items.filter((h) => h.id !== item.id), item]);
    setSelectedId(item.id);
    setLoading(false);
    setError("");
  }, []);
  return <HouseholdContext.Provider value={{ households, selectedId, household: households.find((h) => h.id === selectedId) ?? null,
    loading, error, selectHousehold, refreshHouseholds, confirmHouseholds, addConfirmedHousehold }}>{children}</HouseholdContext.Provider>;
}
export function HouseholdProvider({ children }: { children: React.ReactNode }) {
  const { session, loading } = useSession();
  return session ? <PrivateHouseholdProvider key={session.user.id}>{children}</PrivateHouseholdProvider> :
    <HouseholdContext.Provider value={{ households: [], selectedId: "", household: null, loading, error: "",
      selectHousehold: () => {}, refreshHouseholds: async () => [], confirmHouseholds: () => {}, addConfirmedHousehold: () => {} }}>{children}</HouseholdContext.Provider>;
}
export function useHousehold() {
  const value = useContext(HouseholdContext);
  if (!value) throw new Error("Missing HouseholdProvider");
  return value;
}
export function HouseholdSelector() {
  const { households, household, selectedId, selectHousehold, loading } = useHousehold();
  if (!household) return null;
  return <div className="household-choice">
    {households.length > 1 ? <label htmlFor="household-select">Gospodarstwo
      <select id="household-select" value={selectedId} disabled={loading} onChange={(e) => selectHousehold(e.target.value)}>
        {households.map((item) => <option key={item.id} value={item.id}>{item.name}{item.source === "demo_seed" ? " · demo" : ""}</option>)}
      </select></label> : <p className="section-description">{household.name}</p>}
    {household.source === "demo_seed" && <p className="form-warning" data-testid="demo-household-warning">Osobne gospodarstwo demo. Przykładowe cele 2700/1600 kcal nie są zaleceniem dla Ciebie. Makro pozostaje nieznane.</p>}
  </div>;
}
