"use client";

import { useActionState } from "react";

import { inviteAction, type InviteState } from "@/app/(internal)/invite/actions";
import { FormAlert, SubmitButton } from "@/components/auth-page";
import { FormField } from "@/components/form-field";

const initialState: InviteState = { error: null, fieldErrors: {}, values: { full_name: "", email: "" }, invited: null };

export function InviteForm() {
  const [state, formAction, pending] = useActionState(inviteAction, initialState);

  return (
    // Re-mount after each successful invite so the inputs reset.
    <form key={state.invited?.email ?? "new"} action={formAction} className="space-y-4" noValidate>
      {state.invited && (
        <p role="status" className="rounded-md bg-apple-soft px-3 py-2 text-sm text-ink-soft">
          {state.invited.resent ? "Sent a new invite to " : "Invite sent to "}
          <strong className="font-medium text-ink">{state.invited.full_name}</strong> ({state.invited.email}).
        </p>
      )}
      {state.error && <FormAlert>{state.error}</FormAlert>}
      <FormField
        id="invite-name"
        name="full_name"
        label="Full name"
        autoComplete="off"
        defaultValue={state.values.full_name}
        error={state.fieldErrors.full_name}
      />
      <FormField
        id="invite-email"
        name="email"
        label="Work email"
        type="email"
        autoComplete="off"
        defaultValue={state.values.email}
        error={state.fieldErrors.email}
      />
      <SubmitButton pending={pending} label="Send invite" pendingLabel="Sending…" />
    </form>
  );
}
