import type { Metadata } from "next";
import Link from "next/link";

import { LocalTime } from "@/components/local-time";
import { StateBadge } from "@/components/state-badge";
import { listLeads } from "@/lib/api";
import type { LeadState } from "@/lib/types";

export const metadata: Metadata = { title: "Leads" };

const PAGE_SIZE = 20;
const FILTERS: { label: string; state?: LeadState }[] = [
  { label: "All" },
  { label: "Pending", state: "PENDING" },
  { label: "Reached out", state: "REACHED_OUT" },
];

export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string; page?: string }>;
}) {
  const params = await searchParams;
  const state = FILTERS.find((f) => f.state === params.state)?.state;
  const page = Math.max(1, Number.parseInt(params.page ?? "1", 10) || 1);

  const data = await listLeads({ state, page, pageSize: PAGE_SIZE });
  const lastPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl">Leads</h1>
          <p className="mt-1 text-sm text-muted">
            {data.total} {data.total === 1 ? "lead" : "leads"}
            {state ? ` · ${FILTERS.find((f) => f.state === state)?.label.toLowerCase()}` : ""}
          </p>
        </div>
        <nav aria-label="Filter by state" className="flex w-full rounded-lg border border-line bg-surface p-1 text-sm sm:w-auto">
          {FILTERS.map((filter) => {
            const active = filter.state === state;
            return (
              <Link
                key={filter.label}
                href={filter.state ? `/leads?state=${filter.state}` : "/leads"}
                aria-current={active ? "page" : undefined}
                className={`flex-1 rounded-md px-3 py-1.5 text-center whitespace-nowrap transition sm:flex-none ${
                  active ? "bg-ink text-white" : "text-ink-soft hover:bg-paper"
                }`}
              >
                {filter.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-line bg-surface">
        {data.items.length === 0 ? (
          <p className="px-4 py-12 text-center text-muted sm:px-6 sm:py-16">
            {state ? "No leads in this state." : "No leads yet. They'll appear here as prospects submit the form."}
          </p>
        ) : (
          <>
          {/* Phones: one card per lead. */}
          <ul className="divide-y divide-line md:hidden">
            {data.items.map((lead) => (
              <li key={lead.id}>
                <Link href={`/leads/${lead.id}`} className="block px-4 py-4 active:bg-paper/60">
                  <div className="flex items-start justify-between gap-3">
                    <span className="min-w-0 font-medium break-words text-ink">
                      {lead.first_name} {lead.last_name}
                    </span>
                    <StateBadge state={lead.state} />
                  </div>
                  <p className="mt-1 text-sm break-all text-ink-soft">{lead.email}</p>
                  <p className="mt-1 text-xs text-muted">
                    <LocalTime iso={lead.created_at} />
                  </p>
                </Link>
              </li>
            ))}
          </ul>

          {/* Tablets and up: a table. */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line bg-paper/60 text-xs tracking-wide text-muted uppercase">
                <tr>
                  <th scope="col" className="px-6 py-3 font-medium">Name</th>
                  <th scope="col" className="px-6 py-3 font-medium">Email</th>
                  <th scope="col" className="px-6 py-3 font-medium">Submitted</th>
                  <th scope="col" className="px-6 py-3 font-medium">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map((lead) => (
                  <tr key={lead.id} className="group hover:bg-paper/60">
                    <td className="max-w-[16rem] px-6 py-4 font-medium break-words">
                      <Link href={`/leads/${lead.id}`} className="text-ink group-hover:text-accent">
                        {lead.first_name} {lead.last_name}
                      </Link>
                    </td>
                    <td className="max-w-[18rem] truncate px-6 py-4 text-ink-soft" title={lead.email}>
                      {lead.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-ink-soft">
                      <LocalTime iso={lead.created_at} />
                    </td>
                    <td className="px-6 py-4">
                      <StateBadge state={lead.state} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </div>

      {lastPage > 1 && (
        <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm">
          <PageLink page={page - 1} state={state} disabled={page <= 1}>
            ← Previous
          </PageLink>
          <span className="text-muted">
            Page {page} of {lastPage}
          </span>
          <PageLink page={page + 1} state={state} disabled={page >= lastPage}>
            Next →
          </PageLink>
        </nav>
      )}
    </div>
  );
}

function PageLink(props: {
  page: number;
  state?: LeadState;
  disabled: boolean;
  children: React.ReactNode;
}) {
  if (props.disabled) {
    return <span className="px-3 py-1.5 text-muted/60">{props.children}</span>;
  }
  const query = new URLSearchParams({ page: String(props.page) });
  if (props.state) query.set("state", props.state);
  return (
    <Link href={`/leads?${query}`} className="rounded-md px-3 py-1.5 text-accent hover:bg-accent/5">
      {props.children}
    </Link>
  );
}
