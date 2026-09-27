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
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success/10 text-success">
          <svg aria-hidden="true" viewBox="0 0 20 20" className="h-6 w-6" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <h2 className="mt-5 font-serif text-2xl">Thank you{submittedName ? `, ${submittedName}` : ""}.</h2>
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
      <h2 className="font-serif text-2xl">Your details</h2>

      {formError && (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
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
        className="w-full rounded-lg bg-accent px-5 py-3 font-medium text-white transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
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
        className="mt-1.5 block w-full rounded-lg border border-line bg-white px-3.5 py-2.5 text-ink shadow-xs outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 aria-invalid:border-danger"
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
        className={`mt-1.5 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-4 py-6 text-center transition hover:border-accent hover:bg-accent/5 ${
          props.error ? "border-danger" : "border-line"
        }`}
      >
        {props.file ? (
          <>
            <span className="font-medium text-ink">{props.file.name}</span>
            <span className="mt-1 text-sm text-muted">
              {formatBytes(props.file.size)} · Click to choose a different file
            </span>
          </>
        ) : (
          <>
            <span className="font-medium text-accent">Choose a file</span>
            <span id={hintId} className="mt-1 text-sm text-muted">
              PDF, DOC or DOCX, up to 10 MB
            </span>
          </>
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
