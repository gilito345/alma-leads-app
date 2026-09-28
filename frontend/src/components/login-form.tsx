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
        <p role="alert" className="rounded-md border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger">
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
          className="mt-1.5 block w-full rounded-md border border-line bg-surface px-3 py-3 outline-none transition focus:border-accent focus:ring-3 focus:ring-accent/20"
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
          className="mt-1.5 block w-full rounded-md border border-line bg-surface px-3 py-3 outline-none transition focus:border-accent focus:ring-3 focus:ring-accent/20"
        />
      </div>
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-xl bg-accent px-5 py-3 font-medium text-white transition hover:bg-accent-hover disabled:opacity-60"
      >
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
