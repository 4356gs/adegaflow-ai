import { getApiBaseUrl } from "@/lib/server/config";

const REQUEST_HEADERS = ["content-type", "idempotency-key", "x-correlation-id"] as const;
const RESPONSE_HEADERS = ["content-type", "x-correlation-id", "retry-after"] as const;

function safeCorrelationId(value: string | null): string {
  return value && /^[0-9a-f-]{36}$/i.test(value) ? value : crypto.randomUUID();
}

export async function proxyRequest(request: Request, upstreamPath: string): Promise<Response> {
  const upstream = new URL(upstreamPath, getApiBaseUrl());
  upstream.search = new URL(request.url).search;
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    for (const name of RESPONSE_HEADERS) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    const bodyless = [204, 205, 304].includes(response.status);
    return new Response(bodyless ? null : await response.arrayBuffer(), {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    const correlationId = safeCorrelationId(request.headers.get("x-correlation-id"));
    return Response.json(
      {
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: "The API service is temporarily unavailable.",
          details: {},
          correlation_id: correlationId,
        },
      },
      { status: 503, headers: { "X-Correlation-ID": correlationId } },
    );
  }
}
