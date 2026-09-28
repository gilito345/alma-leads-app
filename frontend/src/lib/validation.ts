/**
 * Client-side checks for the public lead form. They mirror the API's rules so people get
 * instant feedback; the API still validates everything itself.
 */

export const MAX_RESUME_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_RESUME_EXTENSIONS = ["pdf", "doc", "docx"] as const;
export const RESUME_ACCEPT_ATTR = ".pdf,.doc,.docx";

export type LeadField = "first_name" | "last_name" | "email" | "resume";
export type FieldErrors = Partial<Record<LeadField, string>>;

export interface LeadFormInput {
  first_name: string;
  last_name: string;
  email: string;
  resume: { name: string; size: number } | null;
}

// Deliberately loose: the API does the authoritative check.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLeadForm(input: LeadFormInput): FieldErrors {
  const errors: FieldErrors = {};

  if (!input.first_name.trim()) errors.first_name = "Enter your first name.";
  else if (input.first_name.trim().length > 100) errors.first_name = "Keep it under 100 characters.";

  if (!input.last_name.trim()) errors.last_name = "Enter your last name.";
  else if (input.last_name.trim().length > 100) errors.last_name = "Keep it under 100 characters.";

  if (!input.email.trim()) errors.email = "Enter your email address.";
  else if (!EMAIL_PATTERN.test(input.email.trim())) errors.email = "Enter a valid email address.";

  if (!input.resume || input.resume.size === 0) {
    errors.resume = "Attach your resume.";
  } else {
    const extension = input.resume.name.split(".").pop()?.toLowerCase() ?? "";
    if (!input.resume.name.includes(".") || !isAcceptedExtension(extension)) {
      errors.resume = "Upload a PDF, DOC or DOCX file.";
    } else if (input.resume.size > MAX_RESUME_BYTES) {
      errors.resume = "The file must be 10 MB or smaller.";
    }
  }

  return errors;
}

export const MIN_PASSWORD_LENGTH = 12;

export type PasswordField = "password" | "confirm_password";

/** Checks for choosing a new password (accepting an invite or resetting). */
export function validateNewPassword(
  password: string,
  confirm: string,
): Partial<Record<PasswordField, string>> {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { password: `Use at least ${MIN_PASSWORD_LENGTH} characters.` };
  }
  if (password !== confirm) return { confirm_password: "Passwords don't match." };
  return {};
}

function isAcceptedExtension(ext: string): boolean {
  return (ACCEPTED_RESUME_EXTENSIONS as readonly string[]).includes(ext);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
