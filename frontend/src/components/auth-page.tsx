/** The centered card layout shared by sign-in and the account pages around it. */
export function AuthPage({
  title,
  subtitle,
  notice,
  footer,
  children,
}: {
  title: string;
  subtitle?: React.ReactNode;
  notice?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 sm:py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-center font-serif text-2xl sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-2 text-center text-sm text-muted">{subtitle}</p>}
        {notice && (
          <p role="status" className="mt-6 rounded-lg bg-accent/5 px-4 py-3 text-center text-sm text-ink-soft">
            {notice}
          </p>
        )}
        <div className="mt-6 rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">{children}</div>
        {footer && <div className="mt-6 space-y-2 text-center text-sm text-muted">{footer}</div>}
      </div>
    </main>
  );
}

export function FormAlert({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
      {children}
    </p>
  );
}

export function SubmitButton({ pending, label, pendingLabel }: { pending: boolean; label: string; pendingLabel: string }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded-lg bg-ink px-4 py-2.5 font-medium text-white transition hover:bg-ink-soft disabled:opacity-60"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}
