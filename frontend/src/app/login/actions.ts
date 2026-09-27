"use server";

import { redirect } from "next/navigation";

import { ApiError, login, logout } from "@/lib/api";
import { clearSession, getAccessToken, safeNextPath, setSession } from "@/lib/session";

export interface LoginState {
  error: string | null;
  email: string;
}

export async function loginAction(_: LoginState, formData: FormData): Promise<LoginState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const next = safeNextPath(String(formData.get("next") ?? ""));

  if (!email || !password) {
    return { error: "Enter your email and password.", email };
  }

  try {
    await setSession(await login(email, password));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 422)) {
      return { error: "That email and password don't match.", email };
    }
    if (error instanceof ApiError && error.status === 502) {
      return { error: "Sign-in is unavailable. Is Supabase running (supabase start)?", email };
    }
    if (error instanceof ApiError && error.status === 429) {
      return { error: "Too many attempts. Wait a minute and try again.", email };
    }
    console.error("Login failed", error);
    return { error: "We couldn't sign you in right now. Please try again.", email };
  }

  redirect(next);
}

export async function logoutAction(): Promise<void> {
  const token = await getAccessToken();
  if (token) await logout(token);
  await clearSession();
  redirect("/login");
}
