"use client";

import Link from "next/link";
import { useActionState } from "react";

import { setPasswordAction, type SetPasswordState } from "@/app/(account)/actions";
import { FormAlert, SubmitButton } from "@/components/auth-page";
import { FormField } from "@/components/form-field";
import type { PasswordLinkFlow } from "@/lib/api";

const initialState: SetPasswordState = { error: null, linkInvalid: false, fieldErrors: {} };

/** Choose a password from an emailed invite or reset link, then land signed in. */
export function SetPasswordForm({ flow, token }: { flow: PasswordLinkFlow; token: string }) {
  const [state, formAction, pending] = useActionState(setPasswordAction, initialState);

  if (state.linkInvalid) return <InvalidLink flow={flow} />;

  return (
    <form action={formAction} className="space-y-4" noValidate>
      <input type="hidden" name="flow" value={flow} />
      <input type="hidden" name="token" value={token} />
      {state.error && <FormAlert>{state.error}</FormAlert>}
      <FormField
        id="set-password"
        name="password"
        label={flow === "invite" ? "Password" : "New password"}
        type="password"
        autoComplete="new-password"
        hint="At least 12 characters."
        error={state.fieldErrors.password}
      />
      <FormField
        id="set-password-confirm"
        name="confirm_password"
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        error={state.fieldErrors.confirm_password}
      />
      <SubmitButton
        pending={pending}
        label={flow === "invite" ? "Create account" : "Save password"}
        pendingLabel="Saving…"
      />
    </form>
  );
}

export function InvalidLink({ flow }: { flow: PasswordLinkFlow }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed text-ink-soft">
      <p className="font-medium text-ink">This link has expired or was already used.</p>
      {flow === "invite" ? (
        <p>Ask the colleague who invited you to send a new invite.</p>
      ) : (
        <p>
          <Link href="/forgot-password" className="text-accent hover:underline">
            Request a new reset link
          </Link>
          .
        </p>
      )}
    </div>
  );
}
