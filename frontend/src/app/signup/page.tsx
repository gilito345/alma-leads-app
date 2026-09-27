import type { Metadata } from "next";
import Link from "next/link";

import { SignupForm } from "@/components/signup-form";
import { getSignupStatus } from "@/lib/api";

export const metadata: Metadata = { title: "Create an account" };

// Depends on whether any accounts exist yet, so always render on request.
export const dynamic = "force-dynamic";

export default async function SignupPage() {
  const status = await getSignupStatus();

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-center font-serif text-3xl">Create an attorney account</h1>
        <p className="mt-2 text-center text-sm text-muted">
          {status.open
            ? "You're setting up the first account for this dashboard."
            : "Accounts give access to every submitted lead."}
        </p>

        <div className="mt-6 rounded-2xl border border-line bg-surface p-6 shadow-sm">
          {status.enabled ? (
            <SignupForm inviteCodeRequired={status.invite_code_required} />
          ) : (
            <p className="text-sm leading-relaxed text-ink-soft">
              Sign-up is closed. Ask an existing attorney to share the team invite code, or to
              create your account for you.
            </p>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
