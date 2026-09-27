import { NextResponse, type NextRequest } from "next/server";

import { apiBaseUrl } from "@/lib/config";

// Resume limit plus room for the text fields; the API enforces the exact limits.
const MAX_BODY_BYTES = 10 * 1024 * 1024 + 64 * 1024;

/**
 * Public form submission. The browser posts here (same origin) and this forwards the
 * multipart body to the API, adding the client's IP so the API can rate-limit per person.
 */
export async function POST(request: NextRequest) {
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > MAX_BODY_BYTES) {
    return tooLarge();
  }

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_BODY_BYTES) {
    return tooLarge();
  }

  // The right-most X-Forwarded-For entry is the one added by the proxy in front of us;
  // entries further left come from the client and can be forged.
  const forwardedFor = request.headers.get("x-forwarded-for");
  const clientIp = forwardedFor?.split(",").at(-1)?.trim();

  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/leads`, {
      method: "POST",
      body,
      headers: {
        "Content-Type": request.headers.get("content-type") ?? "application/octet-stream",
        Accept: "application/json",
        ...(clientIp ? { "X-Forwarded-For": clientIp } : {}),
      },
      cache: "no-store",
    });
    const payload = await response.text();
    return new NextResponse(payload, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch (error) {
    console.error("Lead submission could not reach the API", error);
    return NextResponse.json(
      { error: { code: "upstream_unavailable", message: "Service temporarily unavailable" } },
      { status: 502 },
    );
  }
}

function tooLarge() {
  return NextResponse.json(
    { error: { code: "payload_too_large", message: "Request body is too large" } },
    { status: 413 },
  );
}
