import type { Metadata } from "next";

import { AuthPage } from "@/components/auth-page";
import { InvalidLink, SetPasswordForm } from "@/components/set-password-form";

// The link's token is in this page's URL: never pass it on as a referrer or let it be indexed.
export const metadata: Metadata = { title: "Set up your account", referrer: "no-referrer", robots: { index: false } };

export default async function AcceptInvitePage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <AuthPage title="Set up your account" subtitle="Choose a password to finish joining the leads dashboard.">
      {token ? <SetPasswordForm flow="invite" token={token} /> : <InvalidLink flow="invite" />}
    </AuthPage>
  );
}
