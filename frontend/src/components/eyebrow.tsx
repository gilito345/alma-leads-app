/** A small uppercase section label with a leading dot. */
export function Eyebrow({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <p
      className={`flex items-center gap-2 text-xs font-bold tracking-eyebrow text-brand uppercase ${className}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-moss" />
      {children}
    </p>
  );
}

/** A checklist line: a green rounded-square tick, then the text. */
export function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span
        aria-hidden="true"
        className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-[5px] bg-accent text-white"
      >
        <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
            clipRule="evenodd"
          />
        </svg>
      </span>
      {children}
    </li>
  );
}
