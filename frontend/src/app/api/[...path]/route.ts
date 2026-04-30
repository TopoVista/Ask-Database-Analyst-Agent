import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEFAULT_PRODUCTION_BACKEND_URL = "https://autonomous-decision-intelligence-engine.onrender.com";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL ??
  process.env.NEXT_PUBLIC_BACKEND_API_URL ??
  (process.env.VERCEL ? DEFAULT_PRODUCTION_BACKEND_URL : "http://127.0.0.1:8011")
).replace(/\/+$/, "");

type RouteContext = {
  params: {
    path: string[];
  };
};

async function proxy(request: NextRequest, { params }: RouteContext) {
  const upstreamPath = params.path.join("/");
  const targetUrl = `${BACKEND_API_URL}/api/${upstreamPath}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("connection");
  headers.delete("expect");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const response = await fetch(targetUrl, init);
  const responseHeaders = new Headers(response.headers);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE, proxy as OPTIONS, proxy as HEAD };
