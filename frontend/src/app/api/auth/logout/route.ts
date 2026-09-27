import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/lib/session";

/**
 * Clears the session and sends the user to /login. Pages can't modify cookies, so when a
 * server component finds the session is no longer valid it redirects here.
 */
export function GET(request: NextRequest) {
  const target = new URL("/login", request.url);
  if (request.nextUrl.searchParams.get("reason") === "expired") {
    target.searchParams.set("reason", "expired");
  }
  const response = NextResponse.redirect(target);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
