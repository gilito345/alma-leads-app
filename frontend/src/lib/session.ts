import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { secureCookiesEnabled } from "./config";

export const SESSION_COOKIE = "leads_session";

export async function getSessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

/** For server components and actions behind auth: the token, or a redirect to /login. */
export async function requireSessionToken(): Promise<string> {
  const token = await getSessionToken();
  if (!token) redirect("/login");
  return token;
}

/** Only callable from server actions and route handlers (cookies are read-only in pages). */
export async function setSessionToken(token: string, maxAgeSeconds: number): Promise<void> {
  const store = await cookies();
  store.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: secureCookiesEnabled(),
    sameSite: "lax",
    path: "/",
    maxAge: maxAgeSeconds,
  });
}

export async function clearSessionToken(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}

/** Only allow same-site relative paths as post-login destinations (no open redirects). */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/leads";
  }
  return next;
}
