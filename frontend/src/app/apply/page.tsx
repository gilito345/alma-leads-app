import type { Metadata } from "next";

import { CheckItem, Eyebrow } from "@/components/eyebrow";
import { LeadForm } from "@/components/lead-form";

export const metadata: Metadata = { title: "Get in touch" };

export default function ApplyPage() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-3 py-3 sm:px-6 sm:py-8 lg:py-12">
      <div className="grid gap-3 rounded-3xl bg-apple p-3 sm:gap-6 sm:p-6 lg:grid-cols-[1fr_1.05fr] lg:items-center lg:gap-12 lg:p-12">
        <section className="px-3 pt-5 pb-2 sm:px-4 sm:pt-4 lg:max-w-md lg:px-0 lg:pt-0">
          <Eyebrow>Free consultation</Eyebrow>
          <h1 className="mt-4 text-4xl leading-[1.1] font-medium tracking-display text-ink sm:text-5xl lg:text-[3.5rem]">
            Tell us about <span className="text-brand">yourself.</span>
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-ink sm:text-xl">
            Share your details and resume. An attorney will review your background and reach out
            to talk through your options.
          </p>
          <ul className="mt-7 space-y-3 text-ink-soft">
            <CheckItem>Takes about two minutes</CheckItem>
            <CheckItem>You&apos;ll get a confirmation email right away</CheckItem>
            <CheckItem>Your resume is only visible to our attorneys</CheckItem>
          </ul>
        </section>

        <section className="rounded-2xl bg-surface p-5 shadow-card sm:p-8 lg:p-10">
          <LeadForm />
        </section>
      </div>
    </main>
  );
}
