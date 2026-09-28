"use server";

import { ApiError, inviteAttorney, type InviteResult } from "@/lib/api";

export type InviteField = "full_name" | "email";

export interface InviteState {
  error: string | null;
  fieldErrors: Partial<Record<InviteField, string>>;
  values: { full_name: string; email: string };
  invited: InviteResult | null;
}

export async function inviteAction(_: InviteState, formData: FormData): Promise<InviteState> {
  const fullName = String(formData.get("full_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const values = { full_name: fullName, email };

  const fieldErrors: InviteState["fieldErrors"] = {};
  if (!fullName) fieldErrors.full_name = "Enter their name.";
  if (!email) fieldErrors.email = "Enter their email.";
  if (Object.keys(fieldErrors).length > 0) {
    return { error: null, fieldErrors, values, invited: null };
  }

  try {
    const invited = await inviteAttorney({ email, full_name: fullName });
    // Clear the form for the next invite.
    return { error: null, fieldErrors: {}, values: { full_name: "", email: "" }, invited };
  } catch (error) {
    // redirect() (e.g. on an expired session) signals by throwing; let it through.
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 409) {
      return { error: null, fieldErrors: { email: "This person already has an account." }, values, invited: null };
    }
    if (error.status === 422) {
      return { error: null, fieldErrors: { email: "Enter a valid email." }, values, invited: null };
    }
    return { error: "We couldn't send the invite right now. Please try again.", fieldErrors: {}, values, invited: null };
  }
}
