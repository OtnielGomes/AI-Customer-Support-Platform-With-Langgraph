/** Cookie HMAC checks that run in the Next.js edge/proxy runtime. */

export const CONSOLE_COOKIE = "console_session";
export const PORTAL_COOKIE = "portal_session";

function tokensMatch(provided: string, expected: string): boolean {
  if (provided.length !== expected.length) {
    return false;
  }
  let mismatch = 0;
  for (let index = 0; index < provided.length; index += 1) {
    mismatch |= provided.charCodeAt(index) ^ expected.charCodeAt(index);
  }
  return mismatch === 0;
}

async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function parsePortalSessionEdge(
  value: string | undefined | null,
): Promise<string | null> {
  if (!value || !value.includes("|")) {
    return null;
  }
  const secret = process.env.PORTAL_SESSION_SECRET;
  if (!secret) {
    return null;
  }
  const email = value.split("|")[0]?.trim().toLowerCase() ?? "";
  if (!email) {
    return null;
  }
  const signature = await hmacSha256Hex(secret, email);
  const expected = `${email}|${signature}`;
  if (!tokensMatch(value, expected)) {
    return null;
  }
  return email;
}

export async function isValidConsoleSession(
  value: string | undefined | null,
): Promise<boolean> {
  if (!value) {
    return false;
  }
  const password = process.env.CONSOLE_PASSWORD;
  if (!password) {
    return false;
  }
  const expected = await hmacSha256Hex(password, "console-ok");
  return tokensMatch(value, expected);
}
