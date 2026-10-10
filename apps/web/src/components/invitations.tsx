"use client";
import { useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  currentAuthGeneration,
  errorMessage,
  type Household,
  type Member,
  type Session,
} from "@/lib/api";
export type Invitation = {
  id: string;
  role: "editor" | "viewer";
  member_id: string | null;
  expires_at: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  version: number;
};
type InvitationCreated = Invitation & { token: string };
export type InvitationAccepted = { household: Household; member: Member };
const roleNames = { viewer: "Tylko podgląd", editor: "Może edytować" };
const statuses = {
  pending: "Oczekuje na przyjęcie",
  accepted: "Przyjęte",
  revoked: "Odwołane",
  expired: "Wygasłe",
};
function expiresAt(value: string, timeZone: string) {
  return new Intl.DateTimeFormat("pl-PL", {
    timeZone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
export function InvitationAccept({
  session,
  onAccepted,
}: {
  session: Session;
  onAccepted: (result: InvitationAccepted) => Promise<void>;
}) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accepted, setAccepted] = useState<InvitationAccepted | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const generation = currentAuthGeneration();
    try {
      const result =
        accepted ??
        (await api<InvitationAccepted>("household-invitations/accept", {
          method: "POST",
          session,
          body: { token: token.trim() },
        }));
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      setToken("");
      setAccepted(result);
      await onAccepted(result);
      if (mounted.current) setAccepted(null);
    } catch (problem) {
      if (mounted.current && generation === currentAuthGeneration())
        setError(errorMessage(problem));
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <section className="form-card" data-testid="invitation-accept">
      <h2>Dołącz do gospodarstwa</h2>
      <p className="section-description">
        Masz kod od właściciela? Przyjmij zaproszenie na swoim zalogowanym
        koncie. Kod działa raz i wygasa po 24 godzinach.
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          {!accepted && (
            <label htmlFor="invitation-token">
              Kod zaproszenia
              <input
                id="invitation-token"
                type="password"
                autoComplete="off"
                spellCheck={false}
                required
                pattern="[0-9a-f]{64}"
                maxLength={64}
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
          )}
          {accepted && (
            <p className="form-success" role="status">
              Zaproszenie przyjęte. Trwa odświeżanie dostępu do gospodarstwa.
            </p>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="button" type="submit">
            {busy
              ? "Łączenie…"
              : accepted
                ? "Odśwież dostęp"
                : "Przyjmij zaproszenie"}
          </button>
        </fieldset>
      </form>
      <p className="note">
        Kod nie trafia do adresu strony. Wklej go tylko wtedy, gdy znasz osobę
        zapraszającą.
      </p>
    </section>
  );
}
export function InvitationManager({
  household,
  members,
  session,
}: {
  household: Household;
  members: Member[];
  session: Session;
}) {
  const eligible = members.filter(
    (member) => !member.user_id && !member.is_guest,
  );
  const [memberId, setMemberId] = useState(eligible[0]?.id ?? "");
  const [role, setRole] = useState<"editor" | "viewer">("viewer");
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [created, setCreated] = useState<InvitationCreated | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [attempt, setAttempt] = useState(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    api<{ invitations: Invitation[] }>(`households/${household.id}/invitations`)
      .then((result) => {
        if (active) {
          setInvitations(result.invitations);
          setCreated((current) =>
            current &&
            result.invitations.find((item) => item.id === current.id)
              ?.status !== "pending"
              ? null
              : current,
          );
        }
      })
      .catch((problem) => {
        if (active) setError(errorMessage(problem));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [household.id, attempt]);
  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    const generation = currentAuthGeneration();
    try {
      const result = await api<InvitationCreated>(
        `households/${household.id}/invite`,
        {
          method: "POST",
          session,
          body: { role, member_id: memberId || null },
        },
      );
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      const { token, ...metadata } = result;
      setCreated(metadata.status === "pending" ? { ...metadata, token } : null);
      setInvitations((current) => [
        metadata,
        ...current.filter((item) => item.id !== metadata.id),
      ]);
      setSuccess(
        metadata.status === "pending"
          ? "Zaproszenie utworzone. Przekaż kod tej osobie prywatnie."
          : "To zaproszenie nie jest już aktywne. Utwórz nowe.",
      );
    } catch (problem) {
      if (mounted.current) setError(errorMessage(problem));
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function copy() {
    if (!created) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      if (!navigator.clipboard?.writeText)
        throw new Error("CLIPBOARD_UNAVAILABLE");
      await navigator.clipboard.writeText(created.token);
      if (mounted.current) setSuccess("Kod skopiowany do schowka.");
    } catch {
      if (mounted.current)
        setError(
          "Nie udało się skopiować kodu. Możesz zaznaczyć go i skopiować ręcznie.",
        );
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function revoke(invitation: Invitation) {
    setBusy(true);
    setError("");
    setSuccess("");
    const generation = currentAuthGeneration();
    try {
      const saved = await api<Invitation>(
        `households/${household.id}/invitations/${invitation.id}/revoke`,
        {
          method: "POST",
          session,
          body: { expected_version: invitation.version },
        },
      );
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      setInvitations((current) =>
        current.map((item) => (item.id === saved.id ? saved : item)),
      );
      if (created?.id === saved.id) setCreated(null);
      setSuccess("Zaproszenie odwołane. Ten kod nie zapewnia już dostępu.");
    } catch (problem) {
      if (mounted.current) setError(errorMessage(problem));
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  if (!household.capabilities.can_manage_access) return null;
  return (
    <section className="form-card invitation-manager">
      <h2>Zaproszenia</h2>
      <p className="section-description">
        Tylko właściciel może zapraszać konta i zarządzać ich dostępem.
        Zaproszenia są jednorazowe i ważne przez 24 godziny.
      </p>
      <form data-testid="invitation-create" onSubmit={create}>
        <fieldset disabled={busy || loading}>
          <div className="field-grid">
            <label htmlFor="invite-member">
              Profil domownika
              <select
                id="invite-member"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
              >
                <option value="">Nowy domownik</option>
                {eligible.map((member) => (
                  <option value={member.id} key={member.id}>
                    {member.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor="invite-role">
              Dostęp dla zaproszonej osoby
              <select
                id="invite-role"
                value={role}
                onChange={(e) => setRole(e.target.value as "editor" | "viewer")}
              >
                {Object.entries(roleNames).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="note">
            Wybierz istniejący profil, aby zachować imię, cele i historię. Nowy
            domownik otrzyma nowy profil dopiero po przyjęciu zaproszenia.
          </p>
          <button className="button" type="submit">
            {busy ? "Przetwarzanie…" : "Utwórz zaproszenie"}
          </button>
        </fieldset>
      </form>
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
      {created && (
        <div className="invitation-secret">
          <h3>Kod nowego zaproszenia</h3>
          <output
            className="invitation-code"
            data-testid="invitation-code"
            aria-label="Kod nowego zaproszenia"
          >
            {created.token}
          </output>
          <p className="note">
            Ważny do {expiresAt(created.expires_at, household.timezone)}. Po
            schowaniu lub odświeżeniu strony kod nie będzie ponownie pokazywany
            na liście.
          </p>
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              disabled={busy || loading}
              onClick={() => void copy()}
            >
              Kopiuj kod
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={busy || loading}
              onClick={() => {
                setCreated(null);
                setSuccess("");
              }}
            >
              Schowaj kod
            </button>
          </div>
        </div>
      )}
      <div className="invitation-list">
        <div className="card-heading">
          <h3>Ostatnie zaproszenia</h3>
          <button
            type="button"
            className="secondary-button"
            disabled={busy || loading}
            onClick={() => {
              setLoading(true);
              setAttempt((value) => value + 1);
              setError("");
              setSuccess("");
            }}
          >
            Odśwież zaproszenia
          </button>
        </div>
        {loading ? (
          <p role="status">Pobieranie zaproszeń…</p>
        ) : invitations.length === 0 ? (
          <p className="note">Nie utworzono jeszcze zaproszeń.</p>
        ) : (
          invitations.map((invitation) => (
            <article
              data-testid="invitation-card"
              data-invitation-id={invitation.id}
              key={invitation.id}
            >
              <div>
                <h4>
                  {members.find((member) => member.id === invitation.member_id)
                    ?.display_name ?? "Nowy domownik"}
                </h4>
                <p className="note">
                  {roleNames[invitation.role]} · {statuses[invitation.status]} ·
                  wersja {invitation.version}
                </p>
                <p className="note">
                  Termin: {expiresAt(invitation.expires_at, household.timezone)}
                </p>
              </div>
              {invitation.status === "pending" && (
                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy || loading}
                  onClick={() => void revoke(invitation)}
                >
                  Odwołaj zaproszenie
                </button>
              )}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
export function MemberAccess({
  member,
  household,
  session,
  onSaved,
}: {
  member: Member;
  household: Household;
  session: Session;
  onSaved: (member: Member) => void;
}) {
  const [role, setRole] = useState(
    member.role === "editor" ? "editor" : "viewer",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [conflict, setConflict] = useState(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function save(enabled: boolean) {
    setBusy(true);
    setError("");
    setSuccess("");
    setConflict(false);
    const generation = currentAuthGeneration();
    try {
      const result = await api<Member>(
        `households/${household.id}/members/${member.id}/access`,
        {
          method: "PUT",
          session,
          body: {
            expected_version: member.access_version,
            role,
            access_enabled: enabled,
          },
        },
      );
      if (!mounted.current || generation !== currentAuthGeneration()) return;
      onSaved(result);
      setRole(result.role);
      setSuccess(
        enabled
          ? "Dostęp zapisany i potwierdzony przez serwer."
          : "Dostęp odebrany. Profil i historia celów pozostają w gospodarstwie.",
      );
    } catch (problem) {
      if (mounted.current) {
        setError(errorMessage(problem));
        setConflict(problem instanceof ApiError && problem.status === 409);
      }
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  if (
    !household.capabilities.can_manage_access ||
    !member.user_id ||
    member.user_id === session.user.id ||
    member.is_guest ||
    member.role === "owner"
  )
    return null;
  return (
    <section className="member-access" data-testid="member-access">
      <h4>Dostęp do konta</h4>
      <p className="note">
        {member.access_enabled ? "Aktywny" : "Odebrany"} · wersja dostępu{" "}
        {member.access_version}. Zmiana dostępu zachowuje domownika, cele i ich
        historię.
      </p>
      <fieldset disabled={busy}>
        <label htmlFor={`access-role-${member.id}`}>
          Dostęp domownika {member.display_name}
          <select
            id={`access-role-${member.id}`}
            value={role}
            onChange={(e) => {
              setRole(e.target.value);
              setSuccess("");
            }}
          >
            <option value="viewer">Tylko podgląd</option>
            <option value="editor">Może edytować</option>
          </select>
        </label>
        <div className="button-row">
          <button
            className="secondary-button"
            type="button"
            disabled={role === member.role}
            onClick={() => void save(member.access_enabled)}
          >
            Zapisz dostęp {member.display_name}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => void save(!member.access_enabled)}
          >
            {member.access_enabled ? "Odbierz" : "Przywróć"} dostęp{" "}
            {member.display_name}
          </button>
        </div>
      </fieldset>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {conflict && (
        <p className="form-warning">
          Dostęp zmienił się na innym urządzeniu. Odśwież gospodarstwo przed
          ponownym zapisem.
        </p>
      )}
      {success && (
        <p className="form-success" role="status">
          {success}
        </p>
      )}
    </section>
  );
}
