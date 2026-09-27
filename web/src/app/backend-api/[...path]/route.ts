import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  INTERNAL_API_URL,
  REFRESH_COOKIE,
  clearSessionCookies,
  refreshTokens,
  setSessionCookies,
  type TokenPair,
} from "@/lib/session";

const HOP_BY_HOP = new Set([
  "connection", "keep-alive", "transfer-encoding", "host", "content-length",
  "cookie",
]);

function buildHeaders(req: NextRequest, accessToken: string | undefined): Headers {
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  headers.delete("authorization");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}

function copyResponseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  return headers;
}

async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  let target = `${INTERNAL_API_URL}/${path.join("/")}`;
  if (!target.endsWith("/")) target += "/";
  target += req.nextUrl.search;

  const hasBody = !["GET", "HEAD"].includes(req.method);
  const body = hasBody ? Buffer.from(await req.arrayBuffer()) : undefined;

  const send = (accessToken: string | undefined) =>
    fetch(target, {
      method: req.method,
      headers: buildHeaders(req, accessToken),
      body,
      cache: "no-store",
      redirect: "manual",
    });

  try {
    let accessToken = req.cookies.get(ACCESS_COOKIE)?.value;
    let upstream = await send(accessToken);
    let rotated: TokenPair | null = null;

    if (upstream.status === 401) {
      const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
      rotated = refresh ? await refreshTokens(refresh) : null;
      if (rotated) {
        accessToken = rotated.access;
        upstream = await send(accessToken);
      }
    }

    const res = new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: copyResponseHeaders(upstream),
    });

    if (rotated) setSessionCookies(res, rotated);
    if (upstream.status === 401) clearSessionCookies(res);
    return res;
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
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;

export const dynamic = "force-dynamic";
