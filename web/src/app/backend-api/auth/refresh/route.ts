import { NextRequest, NextResponse } from "next/server";

import {
  REFRESH_COOKIE,
  clearSessionCookies,
  refreshTokens,
  setSessionCookies,
} from "@/lib/session";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  if (!refresh) {
    return NextResponse.json(
      { success: false, message: "No active session.", code: "UNAUTHENTICATED" },
      { status: 401 }
    );
  }

  const tokens = await refreshTokens(refresh);
  if (!tokens) {
    const res = NextResponse.json(
      { success: false, message: "Session expired.", code: "UNAUTHENTICATED" },
      { status: 401 }
    );
    clearSessionCookies(res);
    return res;
  }

  const res = NextResponse.json({ success: true });
  setSessionCookies(res, tokens);
  return res;
}

export const dynamic = "force-dynamic";
