import { describe, expect, it } from "vitest";

import { authorizeBffRequest, isPortalBffPath } from "./bff-policy";

const TICKET = "2c1a4d6e-8f90-4a1b-9c2d-3e4f5a6b7c8d";

describe("isPortalBffPath", () => {
  it("allows customer chat and confirm routes", () => {
    expect(isPortalBffPath("POST", ["portal", "conversations"])).toBe(true);
    expect(isPortalBffPath("POST", ["tickets", TICKET, "messages"])).toBe(true);
    expect(isPortalBffPath("GET", ["tickets", TICKET, "events"])).toBe(true);
    expect(isPortalBffPath("POST", ["tickets", TICKET, "confirm"])).toBe(true);
  });

  it("rejects console-only mutations", () => {
    expect(isPortalBffPath("POST", ["tickets", TICKET, "takeover"])).toBe(false);
    expect(isPortalBffPath("POST", ["tickets", TICKET, "close"])).toBe(false);
    expect(isPortalBffPath("GET", ["analytics", "overview"])).toBe(false);
  });
});

describe("authorizeBffRequest", () => {
  it("denies anonymous callers", () => {
    expect(
      authorizeBffRequest({
        method: "GET",
        path: ["tickets"],
        hasPortalSession: false,
        hasConsoleSession: false,
      }),
    ).toBe("deny");
  });

  it("scopes a portal session to customer paths", () => {
    expect(
      authorizeBffRequest({
        method: "POST",
        path: ["tickets", TICKET, "messages"],
        hasPortalSession: true,
        hasConsoleSession: false,
      }),
    ).toBe("portal");
    expect(
      authorizeBffRequest({
        method: "POST",
        path: ["tickets", TICKET, "close"],
        hasPortalSession: true,
        hasConsoleSession: false,
      }),
    ).toBe("deny");
  });

  it("lets a console session reach operator routes", () => {
    expect(
      authorizeBffRequest({
        method: "POST",
        path: ["tickets", TICKET, "takeover"],
        hasPortalSession: false,
        hasConsoleSession: true,
      }),
    ).toBe("console");
  });
});
