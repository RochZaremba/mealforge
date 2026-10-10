import { ApiStatus } from "@/components/api-status";
export const metadata = { title: "Stan połączenia" };
export default function StatusPage() { return <><div className="page-heading"><p className="eyebrow">STATUS APLIKACJI</p><h1>Stan połączenia</h1><p>Sprawdź, czy MealForge może połączyć się z serwerem.</p></div><ApiStatus/></>; }
