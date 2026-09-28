import Link from "next/link";

import { logoutAction } from "@/app/login/actions";
import { getCurrentUser } from "@/lib/api";

export default async function InternalLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:h-16 sm:px-6">
          <Link href="/leads" className="text-xl font-semibold tracking-heading text-brand">
            Leads
          </Link>
          <div className="flex items-center gap-2 text-sm sm:gap-4">
            <Link href="/invite" className="rounded-md px-3 py-1.5 font-medium text-moss transition hover:bg-apple-soft">
              Invite attorney
            </Link>
            <span className="hidden max-w-[16rem] truncate text-muted sm:inline">{user.full_name}</span>
            <form action={logoutAction}>
              <button
                type="submit"
                className="rounded-md border border-moss px-3 py-1.5 text-moss transition hover:bg-moss hover:text-white"
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
