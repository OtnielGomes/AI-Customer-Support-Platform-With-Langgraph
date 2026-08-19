import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

describe("parsePortalSession", () => {
  beforeEach(() => {
    process.env.PORTAL_SESSION_SECRET = "test-portal-secret";
    process.env.CONSOLE_PASSWORD = "test-console";
    vi.resetModules();
  });

  it("round-trips a signed email", async () => {
    const { parsePortalSession, portalSessionToken } = await import("./auth");
    const token = portalSessionToken("Demo@test.com.br");
    expect(parsePortalSession(token)).toBe("demo@test.com.br");
  });

  it("rejects a forged cookie", async () => {
    const { parsePortalSession, portalSessionToken } = await import("./auth");
    const token = portalSessionToken("demo@test.com.br");
    expect(parsePortalSession(`attacker@test.com.br|${token.split("|")[1]}`)).toBeNull();
    expect(parsePortalSession("not-a-cookie")).toBeNull();
  });
});
