import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  INTERNAL_API_URL,
  REFRESH_COOKIE,
  clearSessionCookies,
} from "@/lib/session";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  if (access) {
    try {
      await fetch(`${INTERNAL_API_URL}/auth/logout/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${access}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(refresh ? { refresh } : {}),
        cache: "no-store",
      });
    } catch {
      // best effort - the session is invalidated client-side regardless
    }
  }
  const res = NextResponse.json({ success: true, message: "Logged out." });
  clearSessionCookies(res);
  return res;
}

export const dynamic = "force-dynamic";
