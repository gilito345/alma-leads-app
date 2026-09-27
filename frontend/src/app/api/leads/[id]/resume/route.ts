import { NextResponse, type NextRequest } from "next/server";

import { apiBaseUrl } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/session";

/**
 * Streams a lead's resume from the API. The browser only ever talks to this origin with its
 * session cookie; the bearer token and the storage bucket stay server-side.
 */
export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "not_authenticated", message: "Not authenticated" } },
      { status: 401 },
    );
  }

  const { id } = await context.params;
  const upstream = await fetch(`${apiBaseUrl()}/api/v1/leads/${encodeURIComponent(id)}/resume`, {
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
