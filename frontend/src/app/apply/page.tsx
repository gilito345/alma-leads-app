import type { Metadata } from "next";

import { LeadForm } from "@/components/lead-form";

export const metadata: Metadata = { title: "Get in touch" };

export default function ApplyPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-xl gap-8 px-4 py-8 sm:px-6 sm:py-12 lg:max-w-6xl lg:grid-cols-[1fr_1.1fr] lg:items-center lg:gap-12 lg:py-20">
      <section className="lg:max-w-md">
        <p className="text-sm font-medium tracking-wide text-accent uppercase">Free consultation</p>
        <h1 className="mt-3 font-serif text-3xl leading-tight text-ink sm:text-4xl lg:text-5xl">
          Tell us about yourself.
        </h1>
        <p className="mt-4 text-base leading-relaxed text-ink-soft sm:mt-5 sm:text-lg">
          Share your details and resume. An attorney will review your background and reach out
          to talk through your options.
        </p>
        <ul className="mt-6 space-y-3 text-ink-soft sm:mt-8">
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

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-8 lg:p-10">
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
