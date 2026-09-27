import type { NextResponse } from "next/server";

export const ACCESS_COOKIE = "pf_access";
export const REFRESH_COOKIE = "pf_refresh";

export const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000/api";

const ACCESS_FALLBACK_SECONDS = 60 * 60;
const REFRESH_FALLBACK_SECONDS = 7 * 24 * 60 * 60;

export interface TokenPair {
  access: string;
  refresh?: string;
}

function secondsUntilExpiry(token: string, fallback: number): number {
  try {
    const payload = token.split(".")[1];
    if (!payload) return fallback;
    const json = JSON.parse(
      Buffer.from(payload.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8")
    ) as { exp?: number };
    if (!payload || typeof json.exp !== "number") return fallback;
    const remaining = json.exp - Math.floor(Date.now() / 1000);
    return remaining > 0 ? remaining : fallback;
  } catch {
    return fallback;
  }
}

function baseCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
  };
}

export function setSessionCookies(res: NextResponse, tokens: TokenPair): void {
  res.cookies.set(ACCESS_COOKIE, tokens.access, {
    ...baseCookieOptions(),
    maxAge: secondsUntilExpiry(tokens.access, ACCESS_FALLBACK_SECONDS),
  });
  if (tokens.refresh) {
    res.cookies.set(REFRESH_COOKIE, tokens.refresh, {
      ...baseCookieOptions(),
      maxAge: secondsUntilExpiry(tokens.refresh, REFRESH_FALLBACK_SECONDS),
    });
  }
}

export function clearSessionCookies(res: NextResponse): void {
  for (const name of [ACCESS_COOKIE, REFRESH_COOKIE]) {
    res.cookies.set(name, "", { ...baseCookieOptions(), maxAge: 0 });
  }
}

export async function refreshTokens(refresh: string): Promise<TokenPair | null> {
  try {
    const res = await fetch(`${INTERNAL_API_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { access?: string; refresh?: string };
    return body.access ? { access: body.access, refresh: body.refresh } : null;
  } catch {
    return null;
  }
}
