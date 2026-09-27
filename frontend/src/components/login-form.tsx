"use client";

import { useActionState } from "react";

import { loginAction, type LoginState } from "@/app/login/actions";

const initialState: LoginState = { error: null, email: "" };

export function LoginForm({ next }: { next: string }) {
  const [state, formAction, pending] = useActionState(loginAction, initialState);

  return (
    <form action={formAction} className="space-y-4">
      <input type="hidden" name="next" value={next} />
      {state.error && (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {state.error}
        </p>
      )}
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          defaultValue={state.email}
          required
          className="mt-1.5 block w-full rounded-lg border border-line bg-white px-3.5 py-2.5 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="mt-1.5 block w-full rounded-lg border border-line bg-white px-3.5 py-2.5 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-ink px-4 py-2.5 font-medium text-white transition hover:bg-ink-soft disabled:opacity-60"
      >
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
