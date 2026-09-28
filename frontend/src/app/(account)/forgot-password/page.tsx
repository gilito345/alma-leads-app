import type { Metadata } from "next";
import Link from "next/link";

import { AuthPage } from "@/components/auth-page";
import { ForgotPasswordForm } from "@/components/forgot-password-form";

export const metadata: Metadata = { title: "Reset your password" };

export default function ForgotPasswordPage() {
  return (
    <AuthPage
      title="Reset your password"
      subtitle="We'll email you a link to choose a new one."
      footer={
        <p>
          Remembered it?{" "}
          <Link href="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <ForgotPasswordForm />
    </AuthPage>
  );
}
