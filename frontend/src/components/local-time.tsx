"use client";

/** Renders a timestamp in the viewer's own time zone (the server doesn't know it). */
export function LocalTime({ iso }: { iso: string }) {
  const date = new Date(iso);
  return (
    <time dateTime={iso} title={date.toISOString()} suppressHydrationWarning>
      {date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
    </time>
  );
}
