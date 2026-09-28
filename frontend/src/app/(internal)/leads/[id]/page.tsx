import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CopyEmailButton } from "@/components/copy-email-button";
import { LocalTime } from "@/components/local-time";
import { MarkReachedOutButton } from "@/components/mark-reached-out-button";
import { ResumeViewer } from "@/components/resume-viewer";
import { StateBadge } from "@/components/state-badge";
import { ApiError, getLead, getResumePreview } from "@/lib/api";
import type { Lead, ResumePreview } from "@/lib/types";

export const metadata: Metadata = { title: "Lead" };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function LeadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID_PATTERN.test(id)) notFound();

  const [lead, preview] = await Promise.all([
    getLead(id).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    // A preview problem (e.g. the file is missing from storage) shouldn't take the page down.
    getResumePreview(id).catch((error: unknown): ResumePreview => {
      if (!(error instanceof ApiError)) throw error; // let redirects through
      return { format: "unavailable", html: null };
    }),
  ]);

  return (
    <div className="max-w-4xl">
      <Link href="/leads" className="text-sm text-accent hover:underline">
        ← All leads
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-medium tracking-heading break-words sm:text-3xl">
            {lead.first_name} {lead.last_name}
          </h1>
          <p className="mt-1 text-sm text-muted">
            Submitted <LocalTime iso={lead.created_at} />
          </p>
        </div>
        <StateBadge state={lead.state} />
      </div>

      <ContactBar lead={lead} />

      <dl className="mt-6 divide-y divide-line rounded-2xl bg-surface shadow-card">
        <Row label="First name">{lead.first_name}</Row>
        <Row label="Last name">{lead.last_name}</Row>
        <Row label="Email">
          <a href={`mailto:${lead.email}`} className="break-all text-accent hover:underline">
            {lead.email}
          </a>
        </Row>
        <Row label="State">
          <StateBadge state={lead.state} />
        </Row>
        {lead.state === "REACHED_OUT" && lead.reached_out_at && (
          <Row label="Reached out">
            <LocalTime iso={lead.reached_out_at} />
            {lead.reached_out_by && <span className="text-muted"> by {lead.reached_out_by.full_name}</span>}
          </Row>
        )}
      </dl>

      <div className="mt-6">
        <ResumeViewer
          leadId={lead.id}
          filename={lead.resume.filename}
          sizeBytes={lead.resume.size_bytes}
          preview={preview}
        />
      </div>
    </div>
  );
}

/** The page's main actions: write to the prospect, then record that it's done. */
function ContactBar({ lead }: { lead: Lead }) {
  const mailto = `mailto:${lead.email}?${new URLSearchParams({
    subject: "Following up on your inquiry",
    body: `Hi ${lead.first_name},\n\n`,
  })
    .toString()
    .replace(/\+/g, "%20")}`;

  return (
    <div className="mt-6 flex flex-col gap-4 rounded-2xl bg-apple px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <div className="flex flex-wrap gap-2">
        <a
          href={mailto}
          className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-medium whitespace-nowrap text-white transition hover:bg-accent-hover"
        >
          <MailIcon />
          Email {lead.first_name}
        </a>
        <CopyEmailButton email={lead.email} />
      </div>
      {lead.state === "PENDING" ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <p className="text-sm text-ink-soft">Contacted them?</p>
          <MarkReachedOutButton leadId={lead.id} />
        </div>
      ) : (
        <p className="text-sm text-ink-soft">Already contacted.</p>
      )}
    </div>
  );
}

function MailIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4" fill="currentColor">
      <path d="M3 4a2 2 0 0 0-2 2v.4l9 5.4 9-5.4V6a2 2 0 0 0-2-2H3Z" />
      <path d="m19 8.7-8.5 5.1a1 1 0 0 1-1 0L1 8.7V14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.7Z" />
    </svg>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 px-4 py-3.5 sm:grid-cols-[10rem_1fr] sm:gap-4 sm:px-6 sm:py-4">
      <dt className="text-[11px] font-bold tracking-[0.08em] text-muted uppercase sm:pt-0.5">{label}</dt>
      <dd className="min-w-0 text-sm break-words text-ink">{children}</dd>
    </div>
  );
}
