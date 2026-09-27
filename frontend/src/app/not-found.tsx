import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-medium text-muted">404</p>
      <h1 className="mt-2 font-serif text-3xl">Page not found</h1>
      <Link href="/apply" className="mt-6 text-accent underline underline-offset-4">
        Go to the application form
      </Link>
    </main>
  );
}
