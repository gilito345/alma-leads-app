import type { Metadata } from "next";

import { AuthPage } from "@/components/auth-page";
import { InvalidLink, SetPasswordForm } from "@/components/set-password-form";

// The link's token is in this page's URL: never pass it on as a referrer or let it be indexed.
export const metadata: Metadata = { title: "Choose a new password", referrer: "no-referrer", robots: { index: false } };

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <AuthPage title="Choose a new password" subtitle="You'll be signed in once it's saved.">
      {token ? <SetPasswordForm flow="reset" token={token} /> : <InvalidLink flow="reset" />}
    </AuthPage>
  );
}
