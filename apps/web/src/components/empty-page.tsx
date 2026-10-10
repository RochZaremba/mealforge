import Link from "next/link";
import { Icon, type IconName } from "./icon";
export function EmptyPage({ title, intro, description, icon, note }: { title: string; intro: string; description: string; icon: IconName; note: string }) {
 return <><div className="page-heading"><p className="eyebrow">TWOJA WSPÓLNA KUCHNIA</p><h1>{title}</h1><p>{intro}</p></div><section className="empty-state"><span className="empty-icon"><Icon name={icon} size={40}/></span><h2>Ta część kuchni jeszcze powstaje</h2><p>{description}</p><p className="note">{note}</p><Link className="button" href="/">Wróć do dzisiejszych posiłków <Icon name="arrow" size={18}/></Link></section></>;
}
