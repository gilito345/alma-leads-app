/**
 * Session cookie names and helpers shared by server code and proxy.ts.
 * No "server-only" import here: proxy.ts uses these too.
 */

export const ACCESS_COOKIE = "leads_access";
export const REFRESH_COOKIE = "leads_refresh";

/** How long the browser keeps the session cookies. Supabase decides when tokens expire. */
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

/** Refresh a little before the access token actually expires. */
const EXPIRY_MARGIN_SECONDS = 60;

export interface SessionTokens {
  access_token: string;
  refresh_token: string;
}

/** True when the JWT is missing, unreadable, or about to expire. Doesn't verify the signature. */
export function accessTokenNeedsRefresh(token: string | undefined, now = Date.now()): boolean {
  if (!token) return true;
  const payload = token.split(".")[1];
  if (!payload) return true;
  try {
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp !== "number" || json.exp * 1000 - now < EXPIRY_MARGIN_SECONDS * 1000;
  } catch {
    return true;
  }
}

export function sessionCookieOptions(secure: boolean) {
  return {
    httpOnly: true,
    secure,
    sameSite: "lax" as const,
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  };
}
