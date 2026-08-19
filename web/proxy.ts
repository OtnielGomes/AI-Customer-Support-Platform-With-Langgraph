import { NextRequest, NextResponse } from "next/server";

import {
  CONSOLE_COOKIE,
  PORTAL_COOKIE,
  isValidConsoleSession,
  parsePortalSessionEdge,
} from "@/lib/auth-edge";

export async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;

  if (path.startsWith("/console")) {
    const token = request.cookies.get(CONSOLE_COOKIE)?.value;
    if (!(await isValidConsoleSession(token))) {
      const login = new URL("/login", request.url);
      login.searchParams.set("next", path);
      return NextResponse.redirect(login);
    }
    return NextResponse.next();
  }

  const portalProtected =
    path === "/" || path.startsWith("/tickets/") || path.startsWith("/chat");
  if (portalProtected) {
    const token = request.cookies.get(PORTAL_COOKIE)?.value;
    if (!(await parsePortalSessionEdge(token))) {
      return NextResponse.redirect(new URL("/portal/login", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/console/:path*", "/", "/tickets/:path*", "/chat/:path*"],
};
