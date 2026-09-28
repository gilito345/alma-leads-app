import type { Metadata } from "next";
import Link from "next/link";

import { AuthPage } from "@/components/auth-page";
import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; reason?: string }>;
}) {
  const { next, reason } = await searchParams;
  return (
    <AuthPage
      title="Attorney sign in"
      subtitle="Access the leads dashboard."
      notice={reason === "expired" ? "Your session expired. Please sign in again." : undefined}
      footer={
        <>
          <p>
            <Link href="/forgot-password" className="text-accent hover:underline">
              Forgot your password?
            </Link>
          </p>
          <p>Need an account? Ask a colleague to invite you.</p>
        </>
      }
    >
      <LoginForm next={next ?? ""} />
    </AuthPage>
  );
}
