"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  api,
  currentAuthGeneration,
  ApiError,
  displayDecimal,
  errorMessage,
  todayForHousehold,
  type Household,
  type MealSlot,
  type Member,
  type Session,
  type SlotSet,
  type Target,
} from "@/lib/api";
import { useSession } from "./session-provider";
import { HouseholdSelector, useHousehold } from "./household-provider";
import {
  InvitationAccept,
  InvitationManager,
  MemberAccess,
  type InvitationAccepted,
} from "./invitations";

function Feedback({ error, success }: { error?: string; success?: string }) {
  return (
    <>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="form-success" role="status">
          {success}
        </p>
      )}
    </>
  );
}
function AuthForm() {
  const { setSession } = useSession();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      if (register) {
        await api("auth/register", {
          method: "POST",
          body: { email, password, display_name: name },
        });
        setRegister(false);
        setPassword("");
        setSuccess("Konto utworzone. Zaloguj się.");
      } else {
        setSession(
          await api<Session>("auth/login", {
            method: "POST",
            body: { email, password },
          }),
        );
        setPassword("");
      }
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="form-card auth-card">
      <h2>{register ? "Załóż konto" : "Zaloguj się"}</h2>
      <p className="section-description">
        Twoje gospodarstwo i cele są prywatne.
      </p>
      <div className="form-tabs">
        <button
          type="button"
          aria-pressed={!register}
          onClick={() => {
            setRegister(false);
            setError("");
            setSuccess("");
          }}
          disabled={busy}
        >
          Logowanie
        </button>
        <button
          type="button"
          aria-pressed={register}
          onClick={() => {
            setRegister(true);
            setError("");
            setSuccess("");
          }}
          disabled={busy}
        >
          Załóż konto
        </button>
      </div>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <label htmlFor="auth-email">
            E-mail
            <input
              id="auth-email"
              type="email"
              autoComplete="username"
              required
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          {register && (
            <label htmlFor="auth-name">
              Twoje imię
              <input
                id="auth-name"
                autoComplete="given-name"
                required
                maxLength={80}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label htmlFor="auth-password">
            Hasło
            <input
              id="auth-password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <p className="note">Hasło powinno mieć od 12 do 128 znaków.</p>
          <Feedback error={error} success={success} />
          <button className="button" type="submit">
            {busy ? "Łączenie…" : register ? "Utwórz konto" : "Zaloguj się"}
          </button>
        </fieldset>
      </form>
    </section>
  );
}
const goalNames: Record<string, string> = {
  custom: "Indywidualny",
  maintenance: "Utrzymanie",
  cut: "Redukcja",
  recomposition: "Rekompozycja",
  bulk: "Masa",
};
const targetFields = [
  ["kcal_target", "Kalorie (kcal)"],
  ["protein_target_g", "Białko (g)"],
  ["carbs_target_g", "Węglowodany (g)"],
  ["fat_target_g", "Tłuszcze (g)"],
] as const;
function TargetSummary({ target }: { target: Target | null }) {
  return (
    <>
    {target && <p className="note">{target.source === "demo_seed" ? "Przykładowy cel demo — nie jest zaleceniem." : "Cel ustawiony przez domownika."}</p>}
    <dl className="target-summary" data-testid="target-summary">
      {targetFields.map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd
            data-testid={
              {
                kcal_target: "target-kcal",
                protein_target_g: "target-protein",
                carbs_target_g: "target-carbs",
                fat_target_g: "target-fat",
              }[key]
            }
          >
            {displayDecimal(target?.[key])}
          </dd>
        </div>
      ))}
    </dl>
    </>
  );
}
function MemberCard({
  member,
  household,
  session,
  onSaved,
  onAccessSaved,
}: {
  member: Member;
  household: Household;
  session: Session;
  onSaved: (target: Target) => void;
  onAccessSaved: (member: Member) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState<Target[] | null>(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const target = member.nutrition_target;
  const [values, setValues] = useState({
    kcal_target: target?.kcal_target ?? "",
    protein_target_g: target?.protein_target_g ?? "",
    carbs_target_g: target?.carbs_target_g ?? "",
    fat_target_g: target?.fat_target_g ?? "",
    goal_type: target?.goal_type ?? "custom",
    valid_from: target?.valid_from ?? todayForHousehold(household.timezone),
  });
  const base = `households/${household.id}/members/${member.id}/nutrition-target`;
  const canEdit = household.capabilities.can_edit;
  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    setConflict(false);
    const body = {
      expected_version: member.version,
      ...values,
      ...Object.fromEntries(
        targetFields.map(([key]) => [
          key,
          values[key].trim() === ""
            ? null
            : values[key].trim().replace(",", "."),
        ]),
      ),
    };
    try {
      const saved = await api<Target>(base, { method: "PUT", body, session });
      onSaved(saved);
      setEditing(false);
      setHistory(null);
      setSuccess("Cele zapisane i potwierdzone przez serwer.");
    } catch (problem) {
      setError(errorMessage(problem));
      setConflict(problem instanceof ApiError && problem.status === 409);
    } finally {
      setBusy(false);
    }
  }
  async function loadHistory() {
    setHistoryBusy(true);
    setError("");
    try {
      setHistory((await api<{ history: Target[] }>(`${base}/history`)).history);
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setHistoryBusy(false);
    }
  }
  return (
    <section
      className="form-card member-card"
      data-testid="member-card"
      data-member-id={member.id}
    >
      <div className="card-heading">
        <div>
          <h3>{member.display_name}</h3>
          <p className="note">
            {member.user_id
              ? "Osoba z kontem"
              : "Domownik bez osobnego logowania"}{" "}
            · wersja celów {member.version}
          </p>
        </div>
      </div>
      <TargetSummary target={target} />
      {target?.warnings?.map((w) => (
        <p className="form-warning" key={w.code}>
          {w.message}
        </p>
      ))}
      <Feedback error={error} success={success} />
      {conflict && (
        <p className="form-warning">
          Dane zmieniły się na innym urządzeniu. Odśwież gospodarstwo i sprawdź
          aktualną wersję przed ponownym zapisem.
        </p>
      )}
      <div className="button-row">
        {canEdit && (
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              setEditing(!editing);
              setSuccess("");
            }}
            disabled={busy}
          >
            Edytuj cele {member.display_name}
          </button>
        )}
        <button
          className="secondary-button"
          type="button"
          onClick={() => {
            if (history) {
              setHistory(null);
            } else {
              void loadHistory();
            }
          }}
          disabled={historyBusy}
        >
          Historia celów {member.display_name}
        </button>
      </div>
      {editing && canEdit && (
        <form onSubmit={save} className="target-form">
          <fieldset disabled={busy}>
            <p className="note">
              Puste pole oznacza nieznany cel. Wartość 0 pozostaje zerem. Wpisz
              własne cele; MealForge ich nie dobiera.
            </p>
            <div className="field-grid">
              {targetFields.map(([key, label]) => (
                <label key={key} htmlFor={`${member.id}-${key}`}>
                  {label}
                  <input
                    id={`${member.id}-${key}`}
                    inputMode="decimal"
                    type="text"
                    pattern="(?:0|[1-9][0-9]{0,5})(?:[.,][0-9]{1,3})?"
                    maxLength={10}
                    value={values[key]}
                    onChange={(e) =>
                      setValues({ ...values, [key]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
            <label htmlFor={`${member.id}-goal`}>
              Cel
              <select
                id={`${member.id}-goal`}
                value={values.goal_type}
                onChange={(e) =>
                  setValues({ ...values, goal_type: e.target.value })
                }
              >
                {Object.entries(goalNames).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor={`${member.id}-valid-from`}>
              Obowiązuje od
              <input
                id={`${member.id}-valid-from`}
                type="date"
                required
                max={todayForHousehold(household.timezone)}
                value={values.valid_from}
                onChange={(e) =>
                  setValues({ ...values, valid_from: e.target.value })
                }
              />
            </label>
            <p className="note">
              Zapis utworzy nową wersję. Poprzednie cele pozostaną w historii.
            </p>
            <button className="button" type="submit">
              {busy ? "Zapisywanie…" : "Zapisz cele"}
            </button>
          </fieldset>
        </form>
      )}
      <MemberAccess
        member={member}
        household={household}
        session={session}
        onSaved={onAccessSaved}
      />
      {history && (
        <div className="history-list" data-testid="target-history">
          <h4>Historia celów</h4>
          {history.length === 0 ? (
            <p className="note">Nie zapisano jeszcze celów.</p>
          ) : (
            history.map((item) => (
              <article key={item.id}>
                <p>
                  Wersja {item.version} · od {item.valid_from} ·{" "}
                  {goalNames[item.goal_type] ?? item.goal_type}
                </p>
                <TargetSummary target={item} />
              </article>
            ))
          )}
        </div>
      )}
    </section>
  );
}
function SlotEditor({
  initial,
  household,
  session,
}: {
  initial: SlotSet;
  household: Household;
  session: Session;
}) {
  const [slots, setSlots] = useState(initial.slots);
  const [version, setVersion] = useState(initial.version);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dirty, setDirty] = useState(false);
  const [conflict, setConflict] = useState(false);
  const canEdit = household.capabilities.can_edit;
  function change(index: number, patch: Partial<MealSlot>) {
    setSlots((current) =>
      current.map((slot, i) => (i === index ? { ...slot, ...patch } : slot)),
    );
    setDirty(true);
    setSuccess("");
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    setConflict(false);
    try {
      const saved = await api<SlotSet>(
        `households/${household.id}/meal-slot-presets`,
        {
          method: "PUT",
          session,
          body: {
            expected_version: version,
            slots: slots.map((slot) => ({
              id: slot.id,
              name: slot.name.trim(),
              default_time: slot.default_time
                ? slot.default_time.slice(0, 5)
                : null,
              default_share: slot.default_share?.trim()
                ? slot.default_share.trim().replace(",", ".")
                : null,
              repeat_weekly: slot.repeat_weekly,
            })),
          },
        },
      );
      setSlots(saved.slots);
      setVersion(saved.version);
      setDirty(false);
      setSuccess("Posiłki zapisane i potwierdzone przez serwer.");
    } catch (problem) {
      setError(errorMessage(problem));
      setConflict(problem instanceof ApiError && problem.status === 409);
    } finally {
      setBusy(false);
    }
  }
  if (!canEdit)
    return (
      <section className="form-card" data-testid="meal-slots">
        <h2>Posiłki w ciągu dnia</h2>
        <p className="section-description">
          Zapisane ustawienia · wersja {version}. Masz dostęp do podglądu.
        </p>
        <ol className="readonly-slots">
          {slots.map((slot, index) => (
            <li key={slot.id ?? index}>
              <h3>{slot.name}</h3>
              <p className="note">
                Godzina: {slot.default_time?.slice(0, 5) ?? "Nieznana"} · udział
                energii: {slot.default_share ?? "Nieznany"}
              </p>
              <p className="note">
                Powtarzanie co tydzień:{" "}
                {slot.repeat_weekly ? "włączone" : "wyłączone"}
              </p>
            </li>
          ))}
        </ol>
      </section>
    );
  return (
    <section className="form-card">
      <h2>Posiłki w ciągu dnia</h2>
      <p className="section-description">
        Od 1 do 12 posiłków · wersja {version}. Powtarzanie zapisuje preferencję
        dla przyszłego planu tygodnia.
      </p>
      <form onSubmit={save} data-testid="meal-slots">
        <fieldset disabled={busy || !canEdit}>
          {slots.map((slot, index) => (
            <div className="slot-editor" key={slot.id ?? `new-${index}`}>
              <div className="field-grid">
                <label htmlFor={`slot-name-${index}`}>
                  Nazwa posiłku {index + 1}
                  <input
                    id={`slot-name-${index}`}
                    value={slot.name}
                    required
                    maxLength={80}
                    onChange={(e) => change(index, { name: e.target.value })}
                  />
                </label>
                <label htmlFor={`slot-time-${index}`}>
                  Godzina posiłku {index + 1}
                  <input
                    id={`slot-time-${index}`}
                    type="time"
                    value={slot.default_time?.slice(0, 5) ?? ""}
                    onChange={(e) =>
                      change(index, { default_time: e.target.value || null })
                    }
                  />
                </label>
                <label htmlFor={`slot-share-${index}`}>
                  Udział energii posiłku {index + 1}
                  <input
                    id={`slot-share-${index}`}
                    inputMode="decimal"
                    pattern="(?:0(?:[.,][0-9]{1,5})?|1(?:[.,]0{1,5})?)"
                    value={slot.default_share ?? ""}
                    onChange={(e) =>
                      change(index, { default_share: e.target.value || null })
                    }
                  />
                </label>
              </div>
              <p className="note">
                Ułamek dnia od 0 do 1, np. 0,25. Puste pole oznacza nieznany
                udział.
              </p>
              <div className="slot-actions">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={slot.repeat_weekly}
                    onChange={(e) =>
                      change(index, { repeat_weekly: e.target.checked })
                    }
                  />
                  Powtarzaj co tydzień: {slot.name || `posiłek ${index + 1}`}
                </label>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={slots.length <= 1}
                  onClick={() => {
                    setSlots((current) =>
                      current.filter((_, i) => i !== index),
                    );
                    setDirty(true);
                    setSuccess("");
                  }}
                  aria-label={`Usuń posiłek ${index + 1}`}
                >
                  Usuń
                </button>
              </div>
            </div>
          ))}
          <button
            className="secondary-button"
            type="button"
            disabled={slots.length >= 12}
            onClick={() => {
              setSlots([
                ...slots,
                {
                  id: null,
                  name: "",
                  default_time: null,
                  default_share: null,
                  repeat_weekly: false,
                },
              ]);
              setDirty(true);
              setSuccess("");
            }}
          >
            Dodaj posiłek
          </button>
          <Feedback error={error} success={success} />
          {conflict && (
            <p className="form-warning">
              Ustawienia zmieniły się na innym urządzeniu. Odśwież gospodarstwo
              przed ponownym zapisem.
            </p>
          )}
          {dirty && (
            <p className="note">
              Zmiany formularza nie zostały jeszcze zapisane.
            </p>
          )}
          <button className="button" type="submit" disabled={!dirty}>
            {busy ? "Zapisywanie…" : "Zapisz posiłki"}
          </button>
        </fieldset>
      </form>
      {!canEdit && (
        <p className="note">
          Masz dostęp do podglądu. Edycję wykonuje właściciel lub edytor.
        </p>
      )}
    </section>
  );
}
function AuthenticatedHousehold() {
  const {
    session,
    loading,
    error: sessionError,
    refresh,
    setSession,
  } = useSession();
  const { households, selectedId: selected, household, loading: dataLoading, error: householdError,
    selectHousehold: setSelected, refreshHouseholds, confirmHouseholds, addConfirmedHousehold } = useHousehold();
  const selectionRef = useRef(selected);
  useLayoutEffect(() => { selectionRef.current = selected; }, [selected]);
  const [loadedMembers, setMembers] = useState<Member[]>([]);
  const [loadedPresets, setPresets] = useState<SlotSet | null>(null);
  const [loadedHouseholdId, setLoadedHouseholdId] = useState("");
  const members = loadedHouseholdId === selected ? loadedMembers : [];
  const presets = loadedHouseholdId === selected ? loadedPresets : null;
  const [householdName, setHouseholdName] = useState("");
  const [memberName, setMemberName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!session || !selected || dataLoading) return;
    let active = true;
    Promise.all([
      api<{ members: Member[] }>(`households/${selected}/members`),
      api<SlotSet>(`households/${selected}/meal-slot-presets`),
    ])
      .then(([people, slots]) => {
        if (active) {
          setMembers(people.members);
          setPresets(slots);
          setLoadedHouseholdId(selected);
        }
      })
      .catch((problem) => {
        if (active) {
          setError(errorMessage(problem));
          setMembers([]);
          setPresets(null);
          setLoadedHouseholdId("");
          if (problem instanceof ApiError && (problem.status === 403 || problem.status === 404))
            void refreshHouseholds().catch(() => {});
          if (problem instanceof ApiError && problem.status === 401)
            setSession(null);
        }
      });
    return () => {
      active = false;
    };
  }, [session, selected, reload, setSession, dataLoading, refreshHouseholds]);
  async function logout() {
    if (!session) return;
    const generation = currentAuthGeneration();
    setBusy(true);
    setError("");
    try {
      await api("auth/logout", { method: "POST", body: {}, session });
      if (generation !== currentAuthGeneration()) return;
      setSession(null);
      setMembers([]);
      setPresets(null);
      setSelected("");
      setSuccess("");
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }
  async function createHousehold(event: React.FormEvent) {
    event.preventDefault();
    if (!session) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const household = await api<Household>("households", {
        method: "POST",
        session,
        body: {
          name: householdName.trim(),
          timezone: "Europe/Warsaw",
          currency: "PLN",
        },
      });
      addConfirmedHousehold(household);
      setHouseholdName("");
      setSuccess("Gospodarstwo utworzone. Dodaj drugiego domownika.");
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }
  async function addMember(event: React.FormEvent) {
    event.preventDefault();
    if (!session || !selected || dataLoading) return;
    const generation = currentAuthGeneration();
    const householdId = selected;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const member = await api<Member>(`households/${selected}/members`, {
        method: "POST",
        session,
        body: {
          display_name: memberName.trim(),
          is_guest: false,
          role: "viewer",
        },
      });
      if (generation !== currentAuthGeneration() || selectionRef.current !== householdId) return;
      setMembers((current) => [...current, member]);
      setMemberName("");
      setSuccess("Domownik dodany i potwierdzony przez serwer.");
    } catch (problem) {
      if (generation === currentAuthGeneration() && selectionRef.current === householdId) setError(errorMessage(problem));
    } finally {
      if (generation === currentAuthGeneration()) setBusy(false);
    }
  }
  async function joinHousehold(result: InvitationAccepted) {
    const generation = currentAuthGeneration();
    let confirmedSession: Session;
    try {
      confirmedSession = await api<Session>("auth/session");
    } catch (problem) {
      if (
        problem instanceof ApiError &&
        problem.status === 401 &&
        generation === currentAuthGeneration()
      )
        setSession(null);
      throw problem;
    }
    const confirmedHouseholds = await api<{ households: Household[] }>(
      "households",
    );
    if (generation !== currentAuthGeneration()) return;
    const joined = confirmedHouseholds.households.find(
      (item) => item.id === result.household.id,
    );
    if (!joined)
      throw new ApiError(
        404,
        "HOUSEHOLD_NOT_FOUND",
        "Nie można potwierdzić dostępu do gospodarstwa. Odśwież listę gospodarstw.",
      );
    setSession(confirmedSession);
    confirmHouseholds(confirmedHouseholds.households, joined.id);
    setMembers([]);
    setPresets(null);
    setReload((value) => value + 1);
    setError("");
    setSuccess("Zaproszenie przyjęte. Dołączono do gospodarstwa.");
  }
  if (loading)
    return (
      <p className="loading-message" role="status">
        Sprawdzanie sesji…
      </p>
    );
  if (!session)
    return (
      <>
        {sessionError && (
          <div className="form-card">
            <Feedback error={sessionError} />
            <button className="secondary-button" onClick={() => void refresh()}>
              Sprawdź sesję ponownie
            </button>
          </div>
        )}
        <AuthForm />
      </>
    );
  return (
    <div className="household-stack">
      <section className="form-card account-card">
        <div>
          <h2>{session.user.display_name}</h2>
          <p className="note">{session.user.email}</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          disabled={busy}
          onClick={() => void logout()}
        >
          Wyloguj się
        </button>
      </section>
      <Feedback error={error || householdError} success={success} />
      <InvitationAccept
        key={selected || "no-household"}
        session={session}
        onAccepted={joinHousehold}
      />
      {dataLoading && <p role="status">Pobieranie gospodarstwa…</p>}
      {dataLoading ? null : households.length === 0 ? (
        <section className="form-card">
          <h2>Stwórz wspólną kuchnię</h2>
          <form onSubmit={createHousehold}>
            <fieldset disabled={busy}>
              <label htmlFor="household-name">
                Nazwa gospodarstwa
                <input
                  id="household-name"
                  required
                  maxLength={80}
                  value={householdName}
                  onChange={(e) => setHouseholdName(e.target.value)}
                />
              </label>
              <button className="button" type="submit">
                {busy ? "Tworzenie…" : "Utwórz gospodarstwo"}
              </button>
            </fieldset>
          </form>
        </section>
      ) : (
        <>
          <HouseholdSelector />
          {household && (
            <section className="form-card">
              <div className="card-heading">
                <div>
                  <h2>{household.name}</h2>
                  <p className="note">
                    Cele są indywidualne. Posiłki i kuchnia — wspólne.
                  </p>
                </div>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    void refreshHouseholds().catch(() => {});
                    setReload((value) => value + 1);
                    setPresets(null);
                    setMembers([]);
                    setSuccess("");
                  }}
                  disabled={busy || dataLoading}
                >
                  Odśwież gospodarstwo
                </button>
              </div>
            </section>
          )}
          {household &&
            members.map((member) => (
              <MemberCard
                key={`member-${member.id}-${reload}`}
                member={member}
                household={household}
                session={session}
                onAccessSaved={(saved) =>
                  setMembers((current) =>
                    current.map((member) =>
                      member.id === saved.id ? saved : member,
                    ),
                  )
                }
                onSaved={(target) =>
                  setMembers((current) =>
                    current.map((m) =>
                      m.id === member.id
                        ? {
                            ...m,
                            nutrition_target: target,
                            version: target.version,
                          }
                        : m,
                    ),
                  )
                }
              />
            ))}
          {household && presets && household.capabilities.can_manage_access && (
            <InvitationManager
              key={`invite-${household.id}-${reload}`}
              household={household}
              members={members}
              session={session}
            />
          )}
          {household && household.capabilities.can_edit && (
            <section className="form-card">
              <h2>Dodaj domownika</h2>
              <p className="section-description">
                Osobne cele bez osobnego logowania. Właściciel może potem
                połączyć ten profil z kontem przez zaproszenie.
              </p>
              <form onSubmit={addMember}>
                <fieldset disabled={busy}>
                  <label htmlFor="member-name">
                    Imię domownika
                    <input
                      id="member-name"
                      required
                      maxLength={80}
                      value={memberName}
                      onChange={(e) => setMemberName(e.target.value)}
                    />
                  </label>
                  <button className="button" type="submit">
                    {busy ? "Dodawanie…" : "Dodaj domownika"}
                  </button>
                </fieldset>
              </form>
            </section>
          )}
          {household && presets && (
            <SlotEditor
              key={`slots-${household.id}-${reload}`}
              initial={presets}
              household={household}
              session={session}
            />
          )}
        </>
      )}
      <p className="note">
        Planowanie dań i alergie nie są jeszcze dostępne w tym etapie. Nie
        używaj ustawień posiłków jako gotowego planu diety.
      </p>
    </div>
  );
}

export function HouseholdScreen() {
  const { session, loading, error, refresh } = useSession();
  if (loading)
    return (
      <p className="loading-message" role="status">
        Sprawdzanie sesji…
      </p>
    );
  if (!session)
    return (
      <>
        {error && (
          <div className="form-card">
            <Feedback error={error} />
            <button className="secondary-button" onClick={() => void refresh()}>
              Sprawdź sesję ponownie
            </button>
          </div>
        )}
        <AuthForm />
      </>
    );
  return <AuthenticatedHousehold key={session.user.id} />;
}
