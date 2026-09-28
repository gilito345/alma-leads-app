"use client";

import { useState } from "react";

/** Copies an address for attorneys who write from webmail rather than a mail app. */
export function CopyEmailButton({ email }: { email: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked (e.g. insecure context): leave the label as is; the address is on the page.
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-md border border-moss px-4 py-2.5 text-sm font-medium whitespace-nowrap text-moss transition hover:bg-moss hover:text-white"
    >
      <span aria-live="polite">{copied ? "Copied" : "Copy email"}</span>
    </button>
  );
}
