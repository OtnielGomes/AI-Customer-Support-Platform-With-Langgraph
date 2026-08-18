import { cookies } from "next/headers";
import { NextRequest } from "next/server";

import { PORTAL_COOKIE, parsePortalSession } from "@/lib/auth";

export const runtime = "nodejs";

const API_URL = process.env.SUPPORT_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.SUPPORT_API_KEY ?? "";

async function proxy(request: NextRequest, path: string[]): Promise<Response> {
  const target = new URL(`${API_URL}/${path.join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  headers.set("X-API-Key", API_KEY);
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  const jar = await cookies();
  const email = parsePortalSession(jar.get(PORTAL_COOKIE)?.value);
  if (email) {
    headers.set("X-Customer-Email", email);
  }

  const method = request.method;
  const hasBody = method !== "GET" && method !== "HEAD";
  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
  };
  if (hasBody) {
    init.body = request.body;
    (init as RequestInit & { duplex: "half" }).duplex = "half";
  }

  const upstream = await fetch(target, init);
  const out = new Headers();
  const contentTypeOut = upstream.headers.get("content-type");
  if (contentTypeOut) {
    out.set("content-type", contentTypeOut);
  }
  if (contentTypeOut?.includes("text/event-stream")) {
    out.set("cache-control", "no-cache");
    out.set("connection", "keep-alive");
    out.set("x-accel-buffering", "no");
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: out,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
