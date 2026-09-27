import { describe, expect, it } from "vitest";

import { accessTokenNeedsRefresh } from "./session-cookies";

function tokenExpiringAt(expSeconds: number): string {
  const encode = (value: object) =>
    btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${encode({ alg: "ES256" })}.${encode({ sub: "u", exp: expSeconds })}.signature`;
}

describe("accessTokenNeedsRefresh", () => {
  const now = Date.UTC(2026, 8, 27, 12, 0, 0);

  it("keeps a token with plenty of time left", () => {
    expect(accessTokenNeedsRefresh(tokenExpiringAt(now / 1000 + 600), now)).toBe(false);
  });

  it("refreshes a token about to expire", () => {
    expect(accessTokenNeedsRefresh(tokenExpiringAt(now / 1000 + 30), now)).toBe(true);
  });

  it("refreshes an expired token", () => {
    expect(accessTokenNeedsRefresh(tokenExpiringAt(now / 1000 - 5), now)).toBe(true);
  });

  it("refreshes missing or malformed tokens", () => {
    expect(accessTokenNeedsRefresh(undefined, now)).toBe(true);
    expect(accessTokenNeedsRefresh("garbage", now)).toBe(true);
    expect(accessTokenNeedsRefresh("a.%%%.c", now)).toBe(true);
  });
});
