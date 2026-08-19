import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export const CONSOLE_COOKIE = "console_session";
export const PORTAL_COOKIE = "portal_session";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

export function consoleSessionToken(): string {
  const password = requiredEnv("CONSOLE_PASSWORD");
  return createHmac("sha256", password).update("console-ok").digest("hex");
}

export function portalSessionToken(email: string): string {
  const secret = requiredEnv("PORTAL_SESSION_SECRET");
  const payload = email.trim().toLowerCase();
  const signature = createHmac("sha256", secret).update(payload).digest("hex");
  return `${payload}|${signature}`;
}

export function parsePortalSession(value: string | undefined | null): string | null {
  if (!value || !value.includes("|")) {
    return null;
  }
  const email = value.split("|")[0]?.trim().toLowerCase() ?? "";
  if (!email) {
    return null;
  }
  const expected = portalSessionToken(email);
  if (!tokensMatch(value, expected)) {
    return null;
  }
  return email;
}

export function tokensMatch(provided: string, expected: string): boolean {
  const left = Buffer.from(provided);
  const right = Buffer.from(expected);
  if (left.length !== right.length) {
    return false;
  }
  return timingSafeEqual(left, right);
}

export async function isConsoleAuthenticated(): Promise<boolean> {
  const jar = await cookies();
  const value = jar.get(CONSOLE_COOKIE)?.value;
  if (!value) {
    return false;
  }
  try {
    return tokensMatch(value, consoleSessionToken());
  } catch {
    return false;
  }
}

export async function requireConsoleAuth(): Promise<void> {
  if (!(await isConsoleAuthenticated())) {
    throw new Error("Unauthorized");
  }
}

export async function getPortalEmail(): Promise<string | null> {
  const jar = await cookies();
  try {
    return parsePortalSession(jar.get(PORTAL_COOKIE)?.value);
  } catch {
    return null;
  }
}
