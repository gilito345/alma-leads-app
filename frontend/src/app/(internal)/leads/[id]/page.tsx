import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { LocalTime } from "@/components/local-time";
import { MarkReachedOutButton } from "@/components/mark-reached-out-button";
import { StateBadge } from "@/components/state-badge";
import { ApiError, getLead } from "@/lib/api";
import { formatBytes } from "@/lib/validation";

export const metadata: Metadata = { title: "Lead" };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function LeadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID_PATTERN.test(id)) notFound();

  const lead = await getLead(id).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });

  return (
    <div className="max-w-3xl">
      <Link href="/leads" className="text-sm text-accent hover:underline">
        ← All leads
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-serif text-2xl break-words sm:text-3xl">
            {lead.first_name} {lead.last_name}
          </h1>
          <p className="mt-1 text-sm text-muted">
            Submitted <LocalTime iso={lead.created_at} />
          </p>
        </div>
        <StateBadge state={lead.state} />
      </div>

      <dl className="mt-6 divide-y divide-line rounded-xl border border-line bg-surface sm:mt-8">
        <Row label="First name">{lead.first_name}</Row>
        <Row label="Last name">{lead.last_name}</Row>
        <Row label="Email">
          <a href={`mailto:${lead.email}`} className="break-all text-accent hover:underline">
            {lead.email}
          </a>
        </Row>
        <Row label="Resume">
          <a
            href={`/api/leads/${lead.id}/resume`}
            className="break-all text-accent hover:underline"
          >
            {lead.resume.filename}
          </a>
          <span className="ml-2 whitespace-nowrap text-muted">{formatBytes(lead.resume.size_bytes)}</span>
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

      {lead.state === "PENDING" && (
        <div className="mt-6 flex flex-col gap-4 rounded-xl border border-line bg-surface px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="text-sm text-ink-soft">
            Contacted this prospect? Mark the lead so the team knows it&apos;s handled.
          </p>
          <MarkReachedOutButton leadId={lead.id} />
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 px-4 py-3.5 sm:grid-cols-[10rem_1fr] sm:gap-4 sm:px-6 sm:py-4">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="min-w-0 text-sm break-words text-ink">{children}</dd>
    </div>
  );
}
