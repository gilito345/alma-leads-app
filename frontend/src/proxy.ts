import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  accessTokenNeedsRefresh,
  REFRESH_COOKIE,
  sessionCookieOptions,
  type SessionTokens,
} from "@/lib/session-cookies";

/**
 * Runs before every internal page, server action and resume download:
 *
 * - no session at all: page requests go to /login (API routes get a 401);
 * - access token expired or about to: exchange the refresh token (FastAPI -> Supabase Auth)
 *   and pass the new cookies both to this request and back to the browser;
 * - refresh rejected: clear the session and go to /login.
 *
 * This is session plumbing and UX. The API still verifies the token on every request, and
 * that is the security boundary.
 */
export async function proxy(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;

  if (!access && !refresh) {
    return signedOut(request, false);
  }
  if (!accessTokenNeedsRefresh(access)) {
    return NextResponse.next();
  }
  if (!refresh) {
    return signedOut(request, true);
  }

  const tokens = await refreshSession(refresh);
  if (!tokens) {
    return signedOut(request, true);
  }

  // Make the new tokens visible to the page/action rendering this request...
  request.cookies.set(ACCESS_COOKIE, tokens.access_token);
  request.cookies.set(REFRESH_COOKIE, tokens.refresh_token);
  const response = NextResponse.next({ request });
  // ...and store them in the browser.
  const options = sessionCookieOptions((process.env.WEB_ORIGIN ?? "").startsWith("https://"));
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, options);
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, options);
  return response;
}

export default proxy;

export const config = {
  matcher: ["/leads", "/leads/:path*", "/api/leads/:id/resume"],
};

async function refreshSession(refreshToken: string): Promise<SessionTokens | null> {
  const apiUrl = (process.env.API_INTERNAL_URL ?? "").replace(/\/$/, "");
  try {
    const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as SessionTokens;
  } catch (error) {
    console.error("Session refresh failed", error);
    return null;
  }
}

function signedOut(request: NextRequest, expired: boolean) {
  let response: NextResponse;
  if (request.nextUrl.pathname.startsWith("/api/")) {
    response = NextResponse.json(
      { error: { code: "not_authenticated", message: "Not authenticated" } },
      { status: 401 },
    );
  } else {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
    if (expired) login.searchParams.set("reason", "expired");
    response = NextResponse.redirect(login);
  }
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}
