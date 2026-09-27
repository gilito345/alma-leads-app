"use client";

import { useActionState } from "react";

import { signupAction, type SignupField, type SignupState } from "@/app/signup/actions";

const initialState: SignupState = { error: null, fieldErrors: {}, values: { full_name: "", email: "" } };

export function SignupForm({ inviteCodeRequired }: { inviteCodeRequired: boolean }) {
  const [state, formAction, pending] = useActionState(signupAction, initialState);

  return (
    <form action={formAction} className="space-y-4" noValidate>
      {state.error && (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {state.error}
        </p>
      )}
      <Field
        name="full_name"
        label="Full name"
        autoComplete="name"
        defaultValue={state.values.full_name}
        error={state.fieldErrors.full_name}
      />
      <Field
        name="email"
        label="Work email"
        type="email"
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.fieldErrors.email}
      />
      <Field
        name="password"
        label="Password"
        type="password"
        autoComplete="new-password"
        hint="At least 12 characters."
        error={state.fieldErrors.password}
      />
      <Field
        name="confirm_password"
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        error={state.fieldErrors.confirm_password}
      />
      {inviteCodeRequired && (
        <Field
          name="invite_code"
          label="Invite code"
          autoComplete="off"
          hint="Ask an existing attorney for the team's code."
          error={state.fieldErrors.invite_code}
        />
      )}
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-ink px-4 py-2.5 font-medium text-white transition hover:bg-ink-soft disabled:opacity-60"
      >
        {pending ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}

function Field(props: {
  name: SignupField;
  label: string;
  type?: string;
  autoComplete?: string;
  defaultValue?: string;
  hint?: string;
  error?: string;
}) {
  const id = `signup-${props.name}`;
  const describedBy = props.error ? `${id}-error` : props.hint ? `${id}-hint` : undefined;
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {props.label}
      </label>
      <input
        id={id}
        name={props.name}
        type={props.type ?? "text"}
        autoComplete={props.autoComplete}
        defaultValue={props.defaultValue}
        required
        aria-invalid={Boolean(props.error)}
        aria-describedby={describedBy}
        className="mt-1.5 block w-full rounded-lg border border-line bg-white px-3.5 py-2.5 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 aria-invalid:border-danger"
      />
      {props.error ? (
        <p id={`${id}-error`} className="mt-1.5 text-sm text-danger">
          {props.error}
        </p>
      ) : (
        props.hint && (
          <p id={`${id}-hint`} className="mt-1.5 text-xs text-muted">
            {props.hint}
          </p>
        )
      )}
    </div>
  );
}
