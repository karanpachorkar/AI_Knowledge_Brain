import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

const backendHost = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

async function proxyRequest(
  request: NextRequest,
  context: { params: { path: string[] } },
) {
  const path = context.params.path.join("/");
  const target = `${backendHost}/api/v1/${path}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("content-length");
  headers.delete("expect");

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error("API proxy request failed", {
      target,
      method: request.method,
      error,
    });
    return NextResponse.json(
      { detail: "The backend request could not be completed." },
      { status: 502 },
    );
  }
}

export const GET = proxyRequest;
export const HEAD = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
