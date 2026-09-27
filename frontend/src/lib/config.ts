import "server-only";

/** Base URL of the FastAPI service, reachable from the Next.js server (never the browser). */
export function apiBaseUrl(): string {
  const url = process.env.API_INTERNAL_URL;
  if (!url) {
    throw new Error("API_INTERNAL_URL is not set");
  }
  return url.replace(/\/$/, "");
}

/** Mark the session cookie Secure when the site is served over HTTPS. */
export function secureCookiesEnabled(): boolean {
  return (process.env.WEB_ORIGIN ?? "").startsWith("https://");
}
