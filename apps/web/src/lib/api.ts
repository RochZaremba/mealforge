export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export type User = { id: string; email: string; display_name: string };
export type Session = { user: User; csrf_token: string; expires_at: string };
export type Household = {
  id: string;
  name: string;
  timezone: string;
  currency: string;
  role: string;
};
export type Target = {
  id: string;
  version: number;
  kcal_target: string | null;
  protein_target_g: string | null;
  carbs_target_g: string | null;
  fat_target_g: string | null;
  goal_type: string;
  valid_from: string;
  created_at: string;
  warnings: { code: string; message: string }[];
};
export type Member = {
  id: string;
  display_name: string;
  role: string;
  is_guest: boolean;
  user_id: string | null;
  nutrition_target: Target | null;
  version: number;
};
export type MealSlot = {
  id: string | null;
  name: string;
  ordering?: number;
  default_time: string | null;
  default_share: string | null;
  repeat_weekly: boolean;
};
export type SlotSet = { version: number; slots: MealSlot[] };
const mutationKeys = new Map<string, string>();
let authGeneration = 0;
export function currentAuthGeneration() {
  return authGeneration;
}
export function clearMutationKeys() {
  mutationKeys.clear();
  authGeneration += 1;
}
export async function api<T>(
  path: string,
  options: {
    method?: "GET" | "POST" | "PUT";
    body?: unknown;
    session?: Session | null;
  } = {},
): Promise<T> {
  const generation = authGeneration;
  const method = options.method ?? "GET";
  const serialized =
    options.body === undefined ? undefined : JSON.stringify(options.body);
  const action = `${options.session?.user.id ?? "anonymous"}:${method}:${path}:${serialized}`;
  const headers = new Headers();
  let mutationKey: string | undefined;
  const confirmOperation = () => {
    if (
      generation === authGeneration &&
      mutationKey !== undefined &&
      mutationKeys.get(action) === mutationKey
    )
      mutationKeys.delete(action);
  };
  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    if (options.session) {
      headers.set("X-CSRF-Token", options.session.csrf_token);
      let key = mutationKeys.get(action);
      if (!key) {
        key = crypto.randomUUID();
        mutationKeys.set(action, key);
      }
      mutationKey = key;
      headers.set("Idempotency-Key", key);
    }
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, {
      method,
      body: serialized,
      headers,
      credentials: "same-origin",
      cache: "no-store",
      signal: AbortSignal.timeout(14000),
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Brak połączenia. Dane nie zostały potwierdzone. Spróbuj ponownie po odzyskaniu połączenia.",
    );
  }
  if (!response.ok) {
    if (
      response.status === 401 &&
      generation === authGeneration &&
      path !== "auth/login" &&
      path !== "auth/session" &&
      typeof window !== "undefined"
    )
      window.dispatchEvent(new Event("mealforge-session-expired"));
    if (response.status < 500) confirmOperation();
    let payload: { message?: unknown; error_code?: unknown } = {};
    try {
      payload = await response.json();
    } catch {
      /* Only a safe fallback is displayed. */
    }
    const message =
      typeof payload.message === "string" && payload.message.length <= 500
        ? payload.message
        : "Nie udało się wykonać operacji. Sprawdź dane i spróbuj ponownie.";
    throw new ApiError(
      response.status,
      typeof payload.error_code === "string"
        ? payload.error_code
        : "REQUEST_FAILED",
      message,
    );
  }
  if (response.status === 204) {
    confirmOperation();
    return undefined as T;
  }
  let result: T;
  try {
    result = (await response.json()) as T;
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Nie można potwierdzić odpowiedzi serwera. Spróbuj ponownie — zachowamy identyfikator tej operacji.",
    );
  }
  confirmOperation();
  return result;
}
export function errorMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Nie udało się pobrać danych. Spróbuj ponownie.";
}
export function todayForHousehold(timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: string) =>
    parts.find((part) => part.type === type)?.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}
export function displayDecimal(value: string | null | undefined) {
  return value === null || value === undefined
    ? "Nieznane"
    : value.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}
