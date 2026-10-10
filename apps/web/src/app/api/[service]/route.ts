import { NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export async function GET(_request: Request, context: { params: Promise<{ service: string }> }) {
 const { service } = await context.params;
 const headers = { "Cache-Control": "no-store" };
 if (service !== "health" && service !== "ready") return NextResponse.json({ message: "Nie znaleziono usługi." }, { status: 404, headers });
 try {
   const upstream = new URL(`/${service}`, process.env.API_BASE_URL ?? "http://localhost:8000");
   const response = await fetch(upstream, { cache: "no-store", redirect: "error", signal: AbortSignal.timeout(4000), headers: { Accept: "application/json" } });
   const data: unknown = await response.json();
   const expected = service === "health" ? "ok" : "ready";
   if (response.ok && typeof data === "object" && data !== null && "status" in data && data.status === expected) return NextResponse.json({ status: expected }, { headers });
   return NextResponse.json({ message: "Usługa nie jest jeszcze gotowa." }, { status: 503, headers });
 } catch { return NextResponse.json({ message: "Nie można połączyć się z usługą." }, { status: 503, headers }); }
}
