import { NextRequest, NextResponse } from "next/server";

const COOKIE = "console_session";

export function proxy(request: NextRequest) {
  if (!request.nextUrl.pathname.startsWith("/console")) {
    return NextResponse.next();
  }
  const token = request.cookies.get(COOKIE)?.value;
  if (!token) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/console/:path*"],
};
