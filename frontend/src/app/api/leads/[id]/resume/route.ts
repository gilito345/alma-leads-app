import { NextResponse, type NextRequest } from "next/server";

import { apiBaseUrl } from "@/lib/config";
import { ACCESS_COOKIE } from "@/lib/session-cookies";

/**
 * Streams a lead's resume from the API. The browser only ever talks to this origin with its
 * session cookie; the bearer token and the storage bucket stay server-side.
 *
 * `?disposition=inline` asks for a PDF to be displayed (the lead page embeds it); the API
 * ignores it for other file types, which always download.
 */
export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "not_authenticated", message: "Not authenticated" } },
      { status: 401 },
    );
  }

  const { id } = await context.params;
  const inline = request.nextUrl.searchParams.get("disposition") === "inline";
  const query = inline ? "?disposition=inline" : "";
  const upstream = await fetch(`${apiBaseUrl()}/api/v1/leads/${encodeURIComponent(id)}/resume${query}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  }

  const headers = new Headers({
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
  });
  for (const name of ["content-type", "content-disposition", "content-length"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(upstream.body, { status: 200, headers });
}
