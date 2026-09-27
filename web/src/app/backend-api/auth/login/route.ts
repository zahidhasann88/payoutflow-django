import { NextRequest, NextResponse } from "next/server";

import { INTERNAL_API_URL, setSessionCookies } from "@/lib/session";

export async function POST(req: NextRequest): Promise<NextResponse> {
  let upstream: Response;
  try {
    upstream = await fetch(`${INTERNAL_API_URL}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await req.text(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      {
        success: false,
        message: "Could not reach the API server. Is the backend running?",
        code: "API_UNREACHABLE",
      },
      { status: 502 }
    );
  }

  const body = (await upstream.json().catch(() => ({}))) as {
    access?: string;
    refresh?: string;
    user?: unknown;
    message?: string;
    code?: string;
  };

  if (!upstream.ok || !body.access || !body.refresh) {
    return NextResponse.json(
      {
        success: false,
        message: body.message ?? "Login failed.",
        code: body.code ?? "INVALID_CREDENTIALS",
      },
      { status: upstream.ok ? 502 : upstream.status }
    );
  }

  const res = NextResponse.json({ success: true, user: body.user });
  setSessionCookies(res, { access: body.access, refresh: body.refresh });
  return res;
}

export const dynamic = "force-dynamic";
