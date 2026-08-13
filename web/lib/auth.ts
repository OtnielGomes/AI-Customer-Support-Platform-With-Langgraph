import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export const CONSOLE_COOKIE = "console_session";

export function consoleSessionToken(): string {
  const password = process.env.CONSOLE_PASSWORD ?? "";
  return createHmac("sha256", password).update("console-ok").digest("hex");
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
  return tokensMatch(value, consoleSessionToken());
}

export async function requireConsoleAuth(): Promise<void> {
  if (!(await isConsoleAuthenticated())) {
    throw new Error("Unauthorized");
  }
}
