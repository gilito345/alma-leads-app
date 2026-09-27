import "server-only";

import { redirect } from "next/navigation";

import { apiBaseUrl } from "./config";
import { requireAccessToken } from "./session";
import type { SessionTokens } from "./session-cookies";
import type { ApiErrorBody, Lead, LeadPage, LeadState, UserSummary } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: ApiErrorBody["error"]["details"] = null,
  ) {
    super(message);
  }
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    return new ApiError(response.status, body.error.code, body.error.message, body.error.details);
  } catch {
    return new ApiError(response.status, "error", `API request failed (${response.status})`);
  }
}

async function request<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const { token, headers, ...rest } = init;
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    cache: "no-store",
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

/**
 * Call an authenticated endpoint with the current session. An expired or revoked session
 * sends the user to sign in again (via a route handler, since pages can't clear cookies).
 */
async function authed<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await requireAccessToken();
  try {
    return await request<T>(path, { ...init, token });
  } catch (error) {
    // 401: the session is no longer valid. 403: valid Supabase user, but not an attorney.
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/api/auth/logout?reason=expired");
    }
    throw error;
  }
}

export function login(email: string, password: string) {
  return request<SessionTokens>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

/** Revoke the Supabase session. Best effort: signing out locally must never fail. */
export async function logout(accessToken: string): Promise<void> {
  try {
    await fetch(`${apiBaseUrl()}/api/v1/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch (error) {
    console.warn("Sign-out request failed", error);
  }
}

export interface SignupStatus {
  open: boolean;
  invite_code_required: boolean;
  enabled: boolean;
}

export function getSignupStatus() {
  return request<SignupStatus>("/api/v1/auth/signup");
}

export function signup(body: {
  email: string;
  full_name: string;
  password: string;
  invite_code?: string;
}) {
  return request<SessionTokens>("/api/v1/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getCurrentUser() {
  return authed<UserSummary>("/api/v1/auth/me");
}

export function listLeads(params: { state?: LeadState; page?: number; pageSize?: number }) {
  const query = new URLSearchParams();
  if (params.state) query.set("state", params.state);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  const suffix = query.size ? `?${query}` : "";
  return authed<LeadPage>(`/api/v1/leads${suffix}`);
}

export function getLead(id: string) {
  return authed<Lead>(`/api/v1/leads/${encodeURIComponent(id)}`);
}

export function updateLeadState(id: string, state: LeadState) {
  return authed<Lead>(`/api/v1/leads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
}
