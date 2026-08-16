export const BASE_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "bookshelf.access_token";

export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function normalizeDetail(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          const loc = Array.isArray(entry?.loc) ? entry.loc.slice(1).join(".") : "";
          const msg = typeof entry?.msg === "string" ? entry.msg : "invalid value";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("; ");
    }
  }
  return `Request failed (${status})`;
}

export function toQueryString(query: object): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "" && value !== false) params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body; // browser sets the multipart boundary
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { method: options.method ?? "GET", headers, body });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is it running?");
  }

  // A 401 with a stored token means the session is dead; without one it's just
  // a failed login attempt — don't broadcast those.
  if (response.status === 401 && token) {
    tokenStore.clear();
    window.dispatchEvent(new Event("auth:unauthorized"));
  }

  if (!response.ok) {
    const parsed = await response.json().catch(() => null);
    throw new ApiError(response.status, normalizeDetail(response.status, parsed));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
