import type { LeadState } from "@/lib/types";

const STYLES: Record<LeadState, { label: string; className: string }> = {
  PENDING: { label: "Pending", className: "bg-amber-50 text-amber-800 ring-amber-600/20" },
  REACHED_OUT: {
    label: "Reached out",
    className: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  },
};

export function StateBadge({ state }: { state: LeadState }) {
  const style = STYLES[state];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style.className}`}
    >
      {style.label}
    </span>
  );
}
