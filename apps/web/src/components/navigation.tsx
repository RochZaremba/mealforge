"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "./icon";
const links: { href: string; label: string; icon: IconName }[] = [
 { href: "/", label: "Dzisiaj", icon: "today" }, { href: "/plan", label: "Plan", icon: "plan" },
 { href: "/recipes", label: "Przepisy", icon: "recipes" }, { href: "/kitchen", label: "Kuchnia", icon: "kitchen" }, { href: "/shopping", label: "Zakupy", icon: "shopping" },
];
export function Navigation() {
 const pathname = usePathname();
 return <nav className="navigation" aria-label="Główna nawigacja">{links.map(({ href, label, icon }) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}><Icon name={icon}/><span>{label}</span></Link>)}</nav>;
}
