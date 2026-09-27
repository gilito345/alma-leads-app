"use client";

import { useActionState } from "react";

import { markReachedOutAction, type MarkState } from "@/app/(internal)/leads/actions";

export function MarkReachedOutButton({ leadId }: { leadId: string }) {
  const [state, formAction, pending] = useActionState<MarkState>(
    markReachedOutAction.bind(null, leadId),
    { error: null },
  );

  return (
    <form action={formAction}>
      <button
        type="submit"
        disabled={pending}
        className="rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:bg-accent-hover disabled:opacity-60"
      >
        {pending ? "Saving…" : "Mark as reached out"}
      </button>
      {state.error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {state.error}
        </p>
      )}
    </form>
  );
}
