import type { Metadata } from "next";

import { LeadForm } from "@/components/lead-form";

export const metadata: Metadata = { title: "Get in touch" };

export default function ApplyPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-6xl gap-12 px-6 py-12 md:grid-cols-[1fr_1.1fr] md:items-center md:py-20">
      <section className="max-w-md">
        <p className="text-sm font-medium tracking-wide text-accent uppercase">Free consultation</p>
        <h1 className="mt-3 font-serif text-4xl leading-tight text-ink md:text-5xl">
          Tell us about yourself.
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          Share your details and resume. An attorney will review your background and reach out
          to talk through your options.
        </p>
        <ul className="mt-8 space-y-3 text-ink-soft">
          <li className="flex gap-3">
            <Check /> Takes about two minutes
          </li>
          <li className="flex gap-3">
            <Check /> You&apos;ll get a confirmation email right away
          </li>
          <li className="flex gap-3">
            <Check /> Your resume is only visible to our attorneys
          </li>
        </ul>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-6 shadow-sm md:p-10">
        <LeadForm />
      </section>
    </main>
  );
}

function Check() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className="mt-0.5 h-5 w-5 flex-none text-success"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
        clipRule="evenodd"
      />
    </svg>
  );
}
