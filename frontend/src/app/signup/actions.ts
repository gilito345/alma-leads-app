"use server";

import { redirect } from "next/navigation";

import { ApiError, signup } from "@/lib/api";
import { setSessionToken } from "@/lib/session";

export type SignupField = "full_name" | "email" | "password" | "confirm_password" | "invite_code";

export interface SignupState {
  error: string | null;
  fieldErrors: Partial<Record<SignupField, string>>;
  values: { full_name: string; email: string };
}

export async function signupAction(_: SignupState, formData: FormData): Promise<SignupState> {
  const fullName = String(formData.get("full_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("confirm_password") ?? "");
  const inviteCode = String(formData.get("invite_code") ?? "").trim();
  const values = { full_name: fullName, email };

  const fieldErrors: SignupState["fieldErrors"] = {};
  if (!fullName) fieldErrors.full_name = "Enter your name.";
  if (!email) fieldErrors.email = "Enter your email.";
  if (password.length < 12) fieldErrors.password = "Use at least 12 characters.";
  else if (password !== confirm) fieldErrors.confirm_password = "Passwords don't match.";
  if (Object.keys(fieldErrors).length > 0) {
    return { error: null, fieldErrors, values };
  }

  try {
    const { access_token, expires_in } = await signup({
      email,
      full_name: fullName,
      password,
      ...(inviteCode ? { invite_code: inviteCode } : {}),
    });
    await setSessionToken(access_token, expires_in);
  } catch (error) {
    if (!(error instanceof ApiError)) {
      console.error("Sign-up failed", error);
      return { error: "We couldn't create your account right now. Please try again.", fieldErrors, values };
    }
    for (const detail of error.details ?? []) {
      if (["full_name", "email", "password", "invite_code"].includes(detail.field)) {
        fieldErrors[detail.field as SignupField] = fieldMessage(detail.field, detail.message);
      }
    }
    if (error.status === 429) {
      return { error: "Too many attempts. Wait a minute and try again.", fieldErrors, values };
    }
    return {
      error: Object.keys(fieldErrors).length > 0 ? null : error.message,
      fieldErrors,
      values,
    };
  }

  redirect("/leads");
}

function fieldMessage(field: string, apiMessage: string): string {
  if (field === "email") {
    return apiMessage.includes("already") ? "This email already has an account." : "Enter a valid email.";
  }
  if (field === "password") return "Use at least 12 characters.";
  if (field === "invite_code") return "That invite code isn't valid.";
  return "Check this field.";
}
