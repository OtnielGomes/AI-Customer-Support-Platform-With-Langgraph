/** Authorization rules for the Next.js BFF that proxies FastAPI. */

const UUID =
  "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";

type PortalRule = { method: string; pattern: RegExp };

const PORTAL_RULES: PortalRule[] = [
  { method: "GET", pattern: /^portal\/me$/ },
  { method: "POST", pattern: /^portal\/conversations$/ },
  { method: "GET", pattern: /^tickets$/ },
  { method: "GET", pattern: new RegExp(`^tickets/${UUID}$`) },
  { method: "GET", pattern: new RegExp(`^tickets/${UUID}/messages$`) },
  { method: "POST", pattern: new RegExp(`^tickets/${UUID}/messages$`) },
  { method: "GET", pattern: new RegExp(`^tickets/${UUID}/events$`) },
  { method: "POST", pattern: new RegExp(`^tickets/${UUID}/confirm$`) },
];

export type BffDecision = "portal" | "console" | "deny";

export function isPortalBffPath(method: string, path: string[]): boolean {
  const joined = path.filter(Boolean).join("/");
  const verb = method.toUpperCase();
  return PORTAL_RULES.some((rule) => rule.method === verb && rule.pattern.test(joined));
}

export function authorizeBffRequest(input: {
  method: string;
  path: string[];
  hasPortalSession: boolean;
  hasConsoleSession: boolean;
}): BffDecision {
  if (input.hasPortalSession && isPortalBffPath(input.method, input.path)) {
    return "portal";
  }
  if (input.hasConsoleSession) {
    return "console";
  }
  return "deny";
}
