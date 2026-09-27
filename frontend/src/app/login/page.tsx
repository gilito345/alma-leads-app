import type { Metadata } from "next";
import Link from "next/link";

import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; reason?: string }>;
}) {
  const { next, reason } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 sm:py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-center font-serif text-2xl sm:text-3xl">Attorney sign in</h1>
        <p className="mt-2 text-center text-sm text-muted">Access the leads dashboard.</p>
        {reason === "expired" && (
          <p role="status" className="mt-6 rounded-lg bg-accent/5 px-4 py-3 text-center text-sm text-ink-soft">
            Your session expired. Please sign in again.
          </p>
        )}
        <div className="mt-6 rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">
          <LoginForm next={next ?? ""} />
        </div>
        <p className="mt-6 text-center text-sm text-muted">
          New here?{" "}
          <Link href="/signup" className="text-accent hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
