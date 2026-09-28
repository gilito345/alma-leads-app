"use client";

import { useId, useState } from "react";

import type { ApiErrorBody } from "@/lib/types";
import {
  formatBytes,
  RESUME_ACCEPT_ATTR,
  validateLeadForm,
  type FieldErrors,
  type LeadField,
} from "@/lib/validation";

type Status = "idle" | "submitting" | "success";

const FIELDS: LeadField[] = ["first_name", "last_name", "email", "resume"];

export function LeadForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [submittedName, setSubmittedName] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);

    const clientErrors = validateLeadForm({
      first_name: String(data.get("first_name") ?? ""),
      last_name: String(data.get("last_name") ?? ""),
      email: String(data.get("email") ?? ""),
      resume: file ? { name: file.name, size: file.size } : null,
    });
    setErrors(clientErrors);
    setFormError(null);
    if (Object.keys(clientErrors).length > 0) {
      focusFirstError(form, clientErrors);
      return;
    }

    setStatus("submitting");
    try {
      const response = await fetch("/api/leads", { method: "POST", body: data });
      if (response.ok) {
        setSubmittedName(String(data.get("first_name") ?? "").trim());
        setStatus("success");
        return;
      }
      const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
      const serverErrors = fieldErrorsFrom(body);
      setErrors(serverErrors);
      setFormError(messageFor(response.status, body, serverErrors));
      focusFirstError(form, serverErrors);
    } catch {
      setFormError("We couldn't reach the server. Check your connection and try again.");
    }
    setStatus("idle");
  }

  if (status === "success") {
    return (
      <div role="status" className="py-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-apple text-brand">
          <svg aria-hidden="true" viewBox="0 0 20 20" className="h-6 w-6" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <h2 className="mt-5 text-2xl font-medium tracking-heading">Thank you{submittedName ? `, ${submittedName}` : ""}.</h2>
        <p className="mt-3 text-ink-soft">
          We&apos;ve received your information. Check your inbox for a confirmation. An attorney
          will be in touch soon.
        </p>
      </div>
    );
  }

  const submitting = status === "submitting";

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div>
        <h2 className="text-xl font-medium tracking-heading sm:text-2xl">Just a few details, and we&apos;ll take it from here.</h2>
        <p className="mt-2 text-sm text-muted">All fields are required.</p>
      </div>

      {formError && (
        <div role="alert" className="rounded-md border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger">
          {formError}
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField name="first_name" label="First name" autoComplete="given-name" error={errors.first_name} />
        <TextField name="last_name" label="Last name" autoComplete="family-name" error={errors.last_name} />
      </div>
      <TextField name="email" label="Email" type="email" autoComplete="email" error={errors.email} />

      <FileField
        file={file}
        error={errors.resume}
        onChange={(next) => {
          setFile(next);
          setErrors((current) => ({ ...current, resume: undefined }));
        }}
      />

      {/* Honeypot: hidden from people, often filled in by bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input type="text" name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-xl bg-accent px-6 py-3.5 font-medium text-white transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? "Submitting…" : "Submit"}
      </button>
      <p className="text-center text-xs text-muted">
        By submitting, you agree that an attorney may contact you about your inquiry.
      </p>
    </form>
  );
}

function TextField(props: {
  name: LeadField;
  label: string;
  type?: string;
  autoComplete?: string;
  error?: string;
}) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {props.label}
      </label>
      <input
        id={id}
        name={props.name}
        type={props.type ?? "text"}
        autoComplete={props.autoComplete}
        maxLength={props.name === "email" ? 320 : 100}
        required
        aria-invalid={Boolean(props.error)}
        aria-describedby={props.error ? errorId : undefined}
        className="mt-1.5 block w-full rounded-md border border-line bg-surface px-3 py-3 text-ink outline-none transition focus:border-accent focus:ring-3 focus:ring-accent/20 aria-invalid:border-danger"
      />
      {props.error && (
        <p id={errorId} className="mt-1.5 text-sm text-danger">
          {props.error}
        </p>
      )}
    </div>
  );
}

function FileField(props: {
  file: File | null;
  error?: string;
  onChange: (file: File | null) => void;
}) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  return (
    <div>
      <span className="block text-sm font-medium text-ink">Resume / CV</span>
      <label
        htmlFor={id}
        className={`mt-1.5 flex cursor-pointer items-center gap-3 rounded-md border bg-panel px-4 py-3.5 transition hover:bg-apple-soft ${
          props.error ? "border-danger" : "border-transparent"
        }`}
      >
        <UploadIcon />
        {props.file ? (
          <span className="min-w-0">
            <span className="block font-medium break-all text-ink">{props.file.name}</span>
            <span className="block text-sm text-muted">
              {formatBytes(props.file.size)} · Click to choose a different file
            </span>
          </span>
        ) : (
          <span className="min-w-0">
            <span className="block font-medium text-ink-soft">Upload resume or CV</span>
            <span id={hintId} className="block text-sm text-muted">
              PDF, DOC or DOCX, up to 10 MB
            </span>
          </span>
        )}
      </label>
      <input
        id={id}
        name="resume"
        type="file"
        accept={RESUME_ACCEPT_ATTR}
        required
        className="sr-only"
        aria-invalid={Boolean(props.error)}
        aria-describedby={props.error ? errorId : hintId}
        onChange={(event) => props.onChange(event.target.files?.[0] ?? null)}
      />
      {props.error && (
        <p id={errorId} className="mt-1.5 text-sm text-danger">
          {props.error}
        </p>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6 flex-none text-ink-soft" fill="currentColor">
      <path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96ZM14 13v4h-4v-4H7l5-5 5 5h-3Z" />
    </svg>
  );
}

function fieldErrorsFrom(body: ApiErrorBody | null): FieldErrors {
  const errors: FieldErrors = {};
  for (const detail of body?.error.details ?? []) {
    if ((FIELDS as string[]).includes(detail.field)) {
      errors[detail.field as LeadField] ??= friendlyMessage(detail.field as LeadField, detail.message);
    }
  }
  return errors;
}

function friendlyMessage(field: LeadField, apiMessage: string): string {
  if (field === "email") return "Enter a valid email address.";
  if (field === "resume") return apiMessage.endsWith(".") ? apiMessage : `${apiMessage}.`;
  return "Check this field.";
}

function messageFor(status: number, body: ApiErrorBody | null, fieldErrors: FieldErrors): string | null {
  if (status === 413) return "That file is too large. The limit is 10 MB.";
  if (status === 429) return "Too many submissions from your network. Please wait a minute and try again.";
  if (Object.keys(fieldErrors).length > 0) return null;
  return body?.error.message && status < 500
    ? body.error.message
    : "Something went wrong on our side. Please try again in a moment.";
}

function focusFirstError(form: HTMLFormElement, errors: FieldErrors) {
  const first = FIELDS.find((field) => errors[field]);
  if (first) form.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
}
