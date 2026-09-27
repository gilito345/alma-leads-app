import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { secureCookiesEnabled } from "./config";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  sessionCookieOptions,
  type SessionTokens,
} from "./session-cookies";

export async function getAccessToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value ?? null;
}

/**
 * For server components and actions behind auth: the access token, or a redirect to /login.
 * proxy.ts has already refreshed it if it was about to expire.
 */
export async function requireAccessToken(): Promise<string> {
  const token = await getAccessToken();
  if (!token) redirect("/login");
  return token;
}

/** Only callable from server actions and route handlers (cookies are read-only in pages). */
export async function setSession(tokens: SessionTokens): Promise<void> {
  const store = await cookies();
  const options = sessionCookieOptions(secureCookiesEnabled());
  store.set(ACCESS_COOKIE, tokens.access_token, options);
  store.set(REFRESH_COOKIE, tokens.refresh_token, options);
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

/** Only allow same-site relative paths as post-login destinations (no open redirects). */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/leads";
  }
  return next;
}
