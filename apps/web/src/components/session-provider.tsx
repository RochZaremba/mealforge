"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  api,
  ApiError,
  clearMutationKeys,
  currentAuthGeneration,
  errorMessage,
  type Session,
} from "@/lib/api";
type SessionContextValue = {
  session: Session | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  setSession: (session: Session | null) => void;
};
const SessionContext = createContext<SessionContextValue | null>(null);
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionValue] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const setSession = useCallback((value: Session | null) => {
    clearMutationKeys();
    setSessionValue(value);
    setLoading(false);
    setError("");
  }, []);
  const refresh = useCallback(async () => {
    const generation = currentAuthGeneration();
    setLoading(true);
    setError("");
    try {
      const value = await api<Session>("auth/session");
      if (generation === currentAuthGeneration()) setSessionValue(value);
    } catch (problem) {
      if (generation !== currentAuthGeneration()) return;
      setSessionValue(null);
      if (!(problem instanceof ApiError && problem.status === 401))
        setError(errorMessage(problem));
    } finally {
      if (generation === currentAuthGeneration()) setLoading(false);
    }
  }, []);
  useEffect(() => {
    let active = true;
    const generation = currentAuthGeneration();
    const expired = () => {
      clearMutationKeys();
      setSessionValue(null);
      setError("Sesja wygasła. Zaloguj się ponownie.");
    };
    window.addEventListener("mealforge-session-expired", expired);
    api<Session>("auth/session")
      .then((value) => {
        if (active && generation === currentAuthGeneration())
          setSessionValue(value);
      })
      .catch((problem) => {
        if (
          active &&
          generation === currentAuthGeneration() &&
          !(problem instanceof ApiError && problem.status === 401)
        )
          setError(errorMessage(problem));
      })
      .finally(() => {
        if (active && generation === currentAuthGeneration()) setLoading(false);
      });
    return () => {
      active = false;
      window.removeEventListener("mealforge-session-expired", expired);
    };
  }, []);
  return (
    <SessionContext.Provider
      value={{ session, loading, error, refresh, setSession }}
    >
      {children}
    </SessionContext.Provider>
  );
}
export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("Missing SessionProvider");
  return context;
}
