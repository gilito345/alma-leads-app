"use client";

import { useActionState } from "react";

import { requestPasswordResetAction, type ForgotPasswordState } from "@/app/(account)/actions";
import { FormAlert, SubmitButton } from "@/components/auth-page";
import { FormField } from "@/components/form-field";

const initialState: ForgotPasswordState = { sent: false, error: null, email: "" };

export function ForgotPasswordForm() {
  const [state, formAction, pending] = useActionState(requestPasswordResetAction, initialState);

  if (state.sent) {
    return (
      <div role="status" className="space-y-2 text-sm leading-relaxed text-ink-soft">
        <p className="font-medium text-ink">Check your email.</p>
        <p>
          If <strong className="font-medium text-ink">{state.email}</strong> has an account, we&apos;ve sent it a link
          to choose a new password.
        </p>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-4" noValidate>
      {state.error && <FormAlert>{state.error}</FormAlert>}
      <FormField id="forgot-email" name="email" label="Email" type="email" autoComplete="email" defaultValue={state.email} />
      <SubmitButton pending={pending} label="Send reset link" pendingLabel="Sending…" />
    </form>
  );
}
