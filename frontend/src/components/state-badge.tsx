import type { LeadState } from "@/lib/types";

// Pending = waiting on us (honey); reached out = done (brand green). See docs/STYLE_GUIDE.md.
const STYLES: Record<LeadState, { label: string; className: string }> = {
  PENDING: { label: "Pending", className: "bg-honey text-honey-ink" },
  REACHED_OUT: { label: "Reached out", className: "bg-brand text-white" },
};

export function StateBadge({ state }: { state: LeadState }) {
  const style = STYLES[state];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs leading-none font-semibold whitespace-nowrap ${style.className}`}
    >
      {style.label}
    </span>
  );
}
