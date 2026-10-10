"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  displayDecimal,
  errorMessage,
  type Household,
  type Member,
  type SlotSet,
} from "@/lib/api";
import { useSession } from "./session-provider";
const defaults = [
  "Śniadanie",
  "Drugie śniadanie",
  "Obiad",
  "Przekąska",
  "Kolacja",
];
function PrivateOverview() {
  const [data, setData] = useState<{
    household: Household;
    members: Member[];
    presets: SlotSet;
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const { households } = await api<{ households: Household[] }>(
          "households",
        );
        const household = households[0];
        if (!household) return;
        const [people, presets] = await Promise.all([
          api<{ members: Member[] }>(`households/${household.id}/members`),
          api<SlotSet>(`households/${household.id}/meal-slot-presets`),
        ]);
        if (active) setData({ household, members: people.members, presets });
      } catch (problem) {
        if (active) setError(errorMessage(problem));
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);
  if (loading)
    return (
      <p className="loading-message" role="status">
        Pobieranie Waszego rytmu dnia…
      </p>
    );
  if (error)
    return (
      <div className="form-card">
        <p className="form-error" role="alert">
          {error}
        </p>
        <Link className="text-link" href="/household">
          Sprawdź gospodarstwo
        </Link>
      </div>
    );
  if (!data)
    return (
      <section className="form-card">
        <h2>Zacznij od domowników</h2>
        <p className="section-description">
          Utwórz gospodarstwo i ustaw osobne cele.
        </p>
        <Link className="button" href="/household">
          Utwórz gospodarstwo
        </Link>
      </section>
    );
  return (
    <>
      <section aria-labelledby="today-targets">
        <div className="section-heading">
          <h2 id="today-targets">Cele domowników</h2>
          <Link className="text-link" href="/household">
            Edytuj cele
          </Link>
        </div>
        <p className="section-description">
          {data.household.name} · cele, bez wyliczeń spożycia i bez
          zaplanowanych porcji
        </p>
        <div className="today-members">
          {data.members.map((member) => (
            <section className="form-card" key={member.id}>
              <h3>{member.display_name}</h3>
              <dl className="target-summary">
                {(
                  [
                    ["kcal_target", "Kalorie (kcal)"],
                    ["protein_target_g", "Białko (g)"],
                    ["carbs_target_g", "Węglowodany (g)"],
                    ["fat_target_g", "Tłuszcze (g)"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{displayDecimal(member.nutrition_target?.[key])}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </section>
      <MealList
        slots={data.presets.slots.map((slot) => ({
          name: slot.name,
          repeat: slot.repeat_weekly,
        }))}
        confirmed
      />
    </>
  );
}
function MealList({
  slots,
  confirmed = false,
}: {
  slots: { name: string; repeat: boolean }[];
  confirmed?: boolean;
}) {
  return (
    <section aria-labelledby="meals-title">
      <div className="section-heading">
        <h2 id="meals-title">Rytm dnia</h2>
        <span>{slots.length} posiłków</span>
      </div>
      <p className="section-description">
        {confirmed ? "Zapisane ustawienia gospodarstwa" : "Domyślne sloty"} ·
        plan nie został jeszcze utworzony
      </p>
      <ol className="meal-list">
        {slots.map((slot, index) => (
          <li className="meal-card" key={index}>
            <span className="meal-number">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <h3>{slot.name}</h3>
              <p>
                Brak zaplanowanego dania
                {confirmed && slot.repeat
                  ? " · powtarzanie tygodniowe włączone"
                  : ""}
              </p>
            </div>
            <span className="empty-label">Nie zaplanowano</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
export function TodayOverview() {
  const { session } = useSession();
  return session ? (
    <PrivateOverview key={session.user.id} />
  ) : (
    <MealList slots={defaults.map((name) => ({ name, repeat: false }))} />
  );
}
