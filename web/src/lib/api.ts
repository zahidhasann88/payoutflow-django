export const API_BASE = "/backend-api";

export class ApiError extends Error {
  code: string;
  status: number;
  errors?: Record<string, string>;

  constructor(message: string, code: string, status: number, errors?: Record<string, string>) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.errors = errors;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return `${url.pathname}${url.search}`;
}

async function parse(res: Response): Promise<Record<string, unknown>> {
  const text = await res.text();
  try {
    return text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = "/login";
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; query?: Query } = {}
): Promise<T> {
  const { method = "GET", body, query } = options;

  const res = await fetch(buildUrl(path, query), {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
    cache: "no-store",
  });

  const payload = await parse(res);

  if (res.status === 401) {
    redirectToLogin();
  }

  if (!res.ok) {
    throw new ApiError(
      (payload.message as string) || `Request failed (${res.status})`,
      (payload.code as string) || "ERROR",
      res.status,
      payload.errors as Record<string, string> | undefined
    );
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
