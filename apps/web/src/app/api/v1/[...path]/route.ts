import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const UUID =
  "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const routes: [RegExp, readonly string[]][] = [
  [/^auth\/(register|login|logout)$/, ["POST"]],
  [/^auth\/session$/, ["GET"]],
  [/^households$/, ["GET", "POST"]],
  [new RegExp(`^households/${UUID}$`), ["GET"]],
  [new RegExp(`^households/${UUID}/members$`), ["GET", "POST"]],
  [
    new RegExp(`^households/${UUID}/members/${UUID}/nutrition-target$`),
    ["PUT"],
  ],
  [
    new RegExp(`^households/${UUID}/members/${UUID}/nutrition-target/history$`),
    ["GET"],
  ],
  [new RegExp(`^households/${UUID}/meal-slot-presets$`), ["GET", "PUT"]],
  [new RegExp(`^households/${UUID}/invite$`), ["POST"]],
  [new RegExp(`^households/${UUID}/invitations$`), ["GET"]],
  [new RegExp(`^households/${UUID}/invitations/${UUID}/revoke$`), ["POST"]],
  [/^household-invitations\/accept$/, ["POST"]],
  [new RegExp(`^households/${UUID}/members/${UUID}/access$`), ["PUT"]],
  [/^households\/demo$/, ["POST"]],
  [new RegExp(`^households/${UUID}/recipes$`), ["GET", "POST"]],
  [new RegExp(`^households/${UUID}/recipes/${UUID}$`), ["GET", "PUT"]],
  [new RegExp(`^households/${UUID}/recipes/${UUID}/history$`), ["GET"]],
  [new RegExp(`^households/${UUID}/recipe-links$`), ["GET", "POST"]],
  [new RegExp(`^households/${UUID}/recipe-links/${UUID}$`), ["GET"]],
  [new RegExp(`^households/${UUID}/recipe-imports/preview$`), ["POST"]],
];
const privateHeaders = { "Cache-Control": "no-store", Vary: "Cookie" };
function problem(status: number, message: string, error_code: string) {
  return NextResponse.json(
    { message, error_code },
    { status, headers: privateHeaders },
  );
}
async function boundedBody(
  stream: ReadableStream<Uint8Array> | null,
  limit: number,
): Promise<string> {
  if (!stream) return "";
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    void reader.cancel();
  }, 5000);
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (timedOut) throw new Error("BODY_TIMEOUT");
      if (done) break;
      length += value.byteLength;
      if (length > limit) throw new Error("BODY_LIMIT");
      chunks.push(value);
    }
  } finally {
    clearTimeout(timer);
    await reader.cancel();
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}
async function proxy(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const pathname = path.join("/");
  const allowed = routes.find(([pattern]) => pattern.test(pathname));
  if (!allowed) return problem(404, "Nie znaleziono usługi.", "NOT_FOUND");
  if (!allowed[1].includes(request.method))
    return problem(405, "Ta operacja nie jest dostępna.", "METHOD_NOT_ALLOWED");
  const incomingQuery = new URL(request.url).searchParams;
  const pagination = new URLSearchParams();
  const listPage = request.method === "GET" && new RegExp(`^households/${UUID}/(?:recipes|recipe-links)$`).test(pathname);
  const historyPage = request.method === "GET" && new RegExp(`^households/${UUID}/recipes/${UUID}/history$`).test(pathname);
  for (const [name, value] of incomingQuery) {
    if (incomingQuery.getAll(name).length !== 1)
      return problem(400, "Nieprawidłowe parametry strony.", "INVALID_PAGINATION");
    const valid = name === "limit" && (listPage || historyPage) && /^(?:[1-9]|1[0-9]|20)$/.test(value) && Number(value) <= (historyPage ? 5 : 20)
      || name === "after" && listPage && new RegExp(`^${UUID}$`).test(value)
      || name === "before_version" && historyPage && /^[1-9][0-9]{0,8}$/.test(value);
    if (!valid) return problem(400, "Nieprawidłowe parametry strony.", "INVALID_PAGINATION");
    pagination.set(name, value);
  }
  const mutation = request.method !== "GET";
  const origin = request.headers.get("origin");
  let allowedOrigins: string[];
  let production = false;
  try {
    const appEnv = process.env.APP_ENV;
    if (appEnv && !["development", "test", "production"].includes(appEnv))
      throw new Error("INVALID_CONFIGURATION");
    production =
      appEnv === "production" ||
      (!appEnv && process.env.NODE_ENV === "production");
    const configured =
      process.env.TRUSTED_ORIGINS ??
      process.env.APP_BASE_URL ??
      (production ? "" : "http://localhost:3000");
    allowedOrigins = configured.split(",").map((value) => value.trim());
    for (const value of allowedOrigins) {
      const url = new URL(value);
      if (
        !["http:", "https:"].includes(url.protocol) ||
        url.origin !== value ||
        url.username ||
        url.password ||
        (production && url.protocol !== "https:")
      )
        throw new Error("INVALID_CONFIGURATION");
    }
    if (
      production &&
      (!process.env.APP_BASE_URL ||
        !process.env.API_BASE_URL ||
        new URL(process.env.APP_BASE_URL).protocol !== "https:")
    )
      throw new Error("INVALID_CONFIGURATION");
    const upstream = new URL(
      process.env.API_BASE_URL ?? "http://localhost:8000",
    );
    if (
      !["http:", "https:"].includes(upstream.protocol) ||
      upstream.username ||
      upstream.password
    )
      throw new Error("INVALID_CONFIGURATION");
  } catch {
    return problem(
      503,
      "Logowanie nie jest dostępne. Sprawdź konfigurację aplikacji.",
      "AUTH_CONFIGURATION_INVALID",
    );
  }
  if (mutation && (!origin || !allowedOrigins.includes(origin)))
    return problem(
      403,
      "Nie można potwierdzić pochodzenia żądania. Odśwież stronę.",
      "INVALID_ORIGIN",
    );
  if (
    mutation &&
    request.headers.get("content-type")?.split(";")[0].trim() !==
      "application/json"
  )
    return problem(415, "Nieprawidłowy format danych.", "INVALID_CONTENT_TYPE");
  let body: string | undefined;
  try {
    if (mutation) {
      body = await boundedBody(request.body, 16384);
      JSON.parse(body || "{}");
    }
  } catch {
    return problem(413, "Dane są zbyt duże lub nieprawidłowe.", "INVALID_BODY");
  }
  const headers = new Headers({ Accept: "application/json" });
  for (const name of ["cookie", "origin", "x-csrf-token", "idempotency-key"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (mutation) headers.set("Content-Type", "application/json");
  try {
    const upstream = new URL(
      `/api/v1/${pathname}`,
      process.env.API_BASE_URL ?? "http://localhost:8000",
    );
    upstream.search = pagination.toString();
    const response = await fetch(upstream, {
      method: request.method,
      headers,
      body,
      redirect: "error",
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    const responseHeaders = new Headers(privateHeaders);
    for (const cookie of response.headers.getSetCookie()) {
      if (
        production &&
        (!/;\s*Secure(?:;|$)/i.test(cookie) ||
          !/;\s*HttpOnly(?:;|$)/i.test(cookie) ||
          !/;\s*SameSite=(?:Lax|Strict)(?:;|$)/i.test(cookie) ||
          /;\s*Domain=/i.test(cookie))
      )
        return problem(
          503,
          "Nie można bezpiecznie rozpocząć sesji.",
          "UNSAFE_SESSION_COOKIE",
        );
      responseHeaders.append("Set-Cookie", cookie);
    }
    if (response.status === 204)
      return new NextResponse(null, { status: 204, headers: responseHeaders });
    const raw = await boundedBody(response.body, 262144);
    const data: unknown = JSON.parse(raw);
    if (response.status >= 500)
      return problem(
        503,
        "Usługa jest chwilowo niedostępna. Spróbuj ponownie.",
        "SERVICE_UNAVAILABLE",
      );
    return NextResponse.json(data, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return problem(
      503,
      "Brak połączenia z usługą. Sprawdź połączenie i spróbuj ponownie.",
      "SERVICE_UNAVAILABLE",
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
