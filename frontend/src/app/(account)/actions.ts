"use server";

import { redirect } from "next/navigation";

import { ApiError, requestPasswordReset, setPasswordFromLink, type PasswordLinkFlow } from "@/lib/api";
import { setSession } from "@/lib/session";
import { validateNewPassword, type PasswordField } from "@/lib/validation";

export interface ForgotPasswordState {
  sent: boolean;
  error: string | null;
  email: string;
}

export async function requestPasswordResetAction(
  _: ForgotPasswordState,
  formData: FormData,
): Promise<ForgotPasswordState> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) return { sent: false, error: "Enter your email.", email };

  try {
    await requestPasswordReset(email);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { sent: false, error: "Enter a valid email.", email };
    }
    if (error instanceof ApiError && error.status === 429) {
      return { sent: false, error: "Too many requests. Wait a minute and try again.", email };
    }
    console.error("Password reset request failed", error);
    return { sent: false, error: "We couldn't send the link right now. Please try again.", email };
  }
  // Same outcome whether or not the account exists, so this can't be used to probe emails.
  return { sent: true, error: null, email };
}

export interface SetPasswordState {
  error: string | null;
  linkInvalid: boolean;
  fieldErrors: Partial<Record<PasswordField, string>>;
}

export async function setPasswordAction(_: SetPasswordState, formData: FormData): Promise<SetPasswordState> {
  const flow: PasswordLinkFlow = formData.get("flow") === "invite" ? "invite" : "reset";
  const token = String(formData.get("token") ?? "");
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("confirm_password") ?? "");

  const fieldErrors = validateNewPassword(password, confirm);
  if (Object.keys(fieldErrors).length > 0) {
    return { error: null, linkInvalid: false, fieldErrors };
  }

  try {
    await setSession(await setPasswordFromLink(flow, token, password));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { error: null, linkInvalid: true, fieldErrors: {} };
    }
    if (error instanceof ApiError && error.status === 422) {
      return {
        error: null,
        linkInvalid: false,
        fieldErrors: { password: "Choose a stronger password (at least 12 characters)." },
      };
    }
    if (error instanceof ApiError && error.status === 429) {
      return { error: "Too many attempts. Wait a minute and try again.", linkInvalid: false, fieldErrors: {} };
    }
    console.error("Setting password failed", error);
    return { error: "We couldn't save your password right now. Please try again.", linkInvalid: false, fieldErrors: {} };
  }

  redirect("/leads");
}
