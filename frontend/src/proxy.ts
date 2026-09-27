import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "leads_session";

/**
 * Sends signed-out visitors of internal pages to /login. This is a UX convenience only:
 * the API checks the token on every request, and that is the actual security boundary.
 */
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.next();
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(login);
}

export default proxy;

export const config = {
  matcher: ["/leads", "/leads/:path*"],
};
