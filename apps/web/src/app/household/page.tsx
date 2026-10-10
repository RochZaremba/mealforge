import { HouseholdScreen } from "@/components/household";
export const metadata = { title: "Gospodarstwo" };
export default function HouseholdPage() {
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">OSOBNE CELE, WSPÓLNE GOTOWANIE</p>
        <h1>Gospodarstwo</h1>
        <p>Domownicy, cele i Wasz codzienny rytm posiłków.</p>
      </div>
      <HouseholdScreen />
    </>
  );
}
