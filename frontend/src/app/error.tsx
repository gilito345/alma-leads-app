"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto my-16 max-w-lg rounded-xl border border-line bg-surface px-6 py-16 text-center">
      <h1 className="font-medium tracking-heading text-2xl">Something went wrong</h1>
      <p className="mt-2 text-sm text-muted">We couldn&apos;t load this page. The API may be unavailable.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
      >
        Try again
      </button>
    </div>
  );
}
