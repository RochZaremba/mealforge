import Link from "next/link";
import { Icon } from "@/components/icon";
import { TodayOverview } from "@/components/today-overview";
export default function TodayPage() {
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">WSPÓLNA KUCHNIA, OSOBNE CELE</p>
        <h1>Dzisiaj</h1>
        <p>Dobry dzień zaczyna się od spokojnego planu.</p>
      </div>
      <section className="welcome-card" aria-labelledby="welcome-title">
        <div>
          <span className="tag">Zaczynamy od podstaw</span>
          <h2 id="welcome-title">
            Mniej zastanawiania.
            <br />
            Więcej wspólnego gotowania.
          </h2>
          <p>
            To początek Twojej kuchni w MealForge. Zaloguj się, ustaw domowników
            i ich cele. Planowanie dań jest jeszcze przygotowywane.
          </p>
          <Link className="button" href="/household">
            Ustaw gospodarstwo <Icon name="arrow" size={18} />
          </Link>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="plate">
            <div className="plate-inner">
              <Icon name="leaf" size={84} />
            </div>
          </div>
          <div className="art-caption">
            jedna potrawa
            <br />
            <strong>osobne porcje</strong>
          </div>
        </div>
      </section>
      <div className="content-grid">
        <div className="today-overview">
          <TodayOverview />
        </div>
        <aside className="context-stack">
          <section className="info-card">
            <div className="info-icon">
              <Icon name="leaf" />
            </div>
            <h2>Twoje cele, Wasze dania</h2>
            <p>
              Cele ustawisz osobno dla każdej osoby. Kalorie i makro dań pojawią
              się po wdrożeniu zweryfikowanych danych składników.
            </p>
            <span className="note">Brak danych nie oznacza zera.</span>
          </section>
          <section className="info-card subdued">
            <h2>Przestrzeń do gotowania</h2>
            <p>
              Gotowe porcje, zapasy i wspólna lista zakupów pojawią się w
              kolejnych etapach.
            </p>
            <Link className="text-link" href="/kitchen">
              Zajrzyj do kuchni <Icon name="arrow" size={17} />
            </Link>
          </section>
        </aside>
      </div>
    </>
  );
}
