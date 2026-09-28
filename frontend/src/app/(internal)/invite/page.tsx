import type { Metadata } from "next";

import { InviteForm } from "@/components/invite-form";

export const metadata: Metadata = { title: "Invite an attorney" };

export default function InvitePage() {
  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-medium tracking-heading text-2xl sm:text-3xl">Invite an attorney</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        They&apos;ll get an email with a link to choose a password. The link works once and expires after 24 hours;
        invite them again to send a fresh one.
      </p>
      <div className="mt-6 rounded-2xl bg-surface p-5 shadow-card sm:p-6">
        <InviteForm />
      </div>
    </div>
  );
}
