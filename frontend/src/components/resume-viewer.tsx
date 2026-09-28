import type { ResumePreview } from "@/lib/types";
import { formatBytes } from "@/lib/validation";

// Styles for converted Word resumes. The frame is sandboxed with an opaque origin, so it
// can't load the app's web font; a system sans keeps it looking like a document.
const DOCUMENT_CSS = `
  body { margin: 0; padding: 32px 40px; font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Arial, sans-serif; color: #000; background: #fff; }
  h1, h2, h3, h4 { font-weight: 600; line-height: 1.25; margin: 1.2em 0 0.4em; }
  p { margin: 0 0 0.6em; }
  ul, ol { padding-left: 1.4em; margin: 0 0 0.8em; }
  table { border-collapse: collapse; margin: 0 0 1em; }
  td, th { border: 1px solid #e7e8e3; padding: 4px 8px; vertical-align: top; }
  a { color: #207460; }
  @media (max-width: 480px) { body { padding: 20px; } }
`;

/**
 * The resume shown in the page. PDFs use the browser's own viewer; DOCX arrives as sanitized
 * HTML and is rendered in a fully sandboxed frame (no scripts, no same-origin access).
 */
export function ResumeViewer(props: {
  leadId: string;
  filename: string;
  sizeBytes: number;
  preview: ResumePreview;
}) {
  const fileUrl = `/api/leads/${props.leadId}/resume`;
  const inlineUrl = `${fileUrl}?disposition=inline`;

  return (
    <section aria-labelledby="resume-heading" className="overflow-hidden rounded-2xl bg-surface shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3.5 sm:px-6">
        <div className="min-w-0">
          <h2 id="resume-heading" className="text-[11px] font-bold tracking-[0.08em] text-muted uppercase">
            Resume
          </h2>
          <p className="mt-0.5 truncate text-sm text-ink" title={props.filename}>
            {props.filename} <span className="text-muted">· {formatBytes(props.sizeBytes)}</span>
          </p>
        </div>
        <div className="flex gap-2">
          {props.preview.format === "pdf" && (
            <a
              href={inlineUrl}
              target="_blank"
              rel="noopener"
              className="rounded-md border border-moss px-3 py-1.5 text-sm text-moss transition hover:bg-moss hover:text-white"
            >
              Open in new tab
            </a>
          )}
          <a
            href={fileUrl}
            className="rounded-md border border-moss px-3 py-1.5 text-sm text-moss transition hover:bg-moss hover:text-white"
          >
            Download
          </a>
        </div>
      </div>

      {props.preview.format === "pdf" && (
        <>
          {/* Phones' browsers render embedded PDFs poorly, so they get a button instead. */}
          <iframe src={inlineUrl} title={`Resume: ${props.filename}`} className="hidden h-[80vh] min-h-[32rem] w-full md:block" />
          <p className="px-4 py-8 text-center text-sm text-muted md:hidden">
            <a href={inlineUrl} target="_blank" rel="noopener" className="font-medium text-accent hover:underline">
              Open the resume
            </a>{" "}
            to read it full screen.
          </p>
        </>
      )}

      {props.preview.format === "html" && props.preview.html !== null && (
        <iframe
          srcDoc={`<!doctype html><html><head><meta charset="utf-8"><style>${DOCUMENT_CSS}</style></head><body>${props.preview.html}</body></html>`}
          sandbox=""
          title={`Resume: ${props.filename}`}
          className="h-[70vh] min-h-[28rem] w-full md:h-[80vh]"
        />
      )}

      {props.preview.format === "unavailable" && (
        <p className="px-4 py-10 text-center text-sm text-muted sm:px-6">
          This file type can&apos;t be previewed here. Use <span className="font-medium text-ink">Download</span> to open it.
        </p>
      )}
    </section>
  );
}
