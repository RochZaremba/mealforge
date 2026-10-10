import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Navigation } from "@/components/navigation";
import { Icon } from "@/components/icon";
import { PwaRegistration } from "@/components/pwa-registration";
import { SessionProvider } from "@/components/session-provider";
import { HouseholdProvider } from "@/components/household-provider";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "MealForge — wspólna kuchnia", template: "%s | MealForge" },
  description: "Jedna kuchnia, osobne cele. Prywatne planowanie posiłków.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "MealForge", statusBarStyle: "default" },
  icons: { icon: "/icons/icon.svg", apple: "/icons/icon-192.png" },
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#315b46",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pl">
      <body>
        <SessionProvider>
          <HouseholdProvider>
          <a className="skip-link" href="#main-content">
            Przejdź do treści
          </a>
          <div className="app-shell">
            <aside className="sidebar">
              <Link className="brand" href="/" aria-label="MealForge — Dzisiaj">
                <span className="brand-mark">
                  <Icon name="leaf" size={26} />
                </span>
                <span>
                  MealForge<small>Wspólna kuchnia</small>
                </span>
              </Link>
              <Navigation />
              <div className="sidebar-note">
                <Icon name="leaf" />
                <p>
                  Jedna kuchnia.
                  <br />
                  Osobne cele.
                </p>
              </div>
              <Link className="status-link" href="/status">
                <Icon name="signal" size={18} /> Stan połączenia
              </Link>
            </aside>
            <div className="main-shell">
              <header className="topbar">
                <span>Twoja przestrzeń do dobrego jedzenia</span>
                <div className="topbar-links">
                  <Link href="/household">Gospodarstwo</Link>
                  <Link href="/status">
                    Sprawdź połączenie <Icon name="signal" size={18} />
                  </Link>
                </div>
              </header>
              <PwaRegistration />
              <main id="main-content" tabIndex={-1}>
                {children}
              </main>
              <footer className="footer">
                MealForge · prywatna, wspólna kuchnia
              </footer>
            </div>
          </div>
          </HouseholdProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
