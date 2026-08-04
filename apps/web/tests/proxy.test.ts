import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyRequest } from "@/lib/server/proxy";

afterEach(() => vi.unstubAllGlobals());

describe("same-origin proxy", () => {
  it("forwards method, query, JSON body and allowed request headers", async () => {
    const upstream = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return new Response(JSON.stringify({ id: "1" }), {
        status: 201, headers: { "content-type": "application/json", "x-correlation-id": "c" },
      });
    });
    vi.stubGlobal("fetch", upstream);
    const request = new Request("http://web/api/v1/inquiries?limit=3", {
      method: "POST",
      headers: { "content-type": "application/json", "idempotency-key": "key-1", authorization: "secret" },
      body: JSON.stringify({ source: "demo" }),
    });
    const response = await proxyRequest(request, "/api/v1/inquiries");
    const [url, init] = upstream.mock.calls[0] ?? [];
    expect(String(url)).toBe("http://127.0.0.1:8000/api/v1/inquiries?limit=3");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("idempotency-key")).toBe("key-1");
    expect(new Headers(init?.headers).has("authorization")).toBe(false);
    expect(response.status).toBe(201);
    expect(response.headers.get("x-correlation-id")).toBe("c");
  });

  it("does not attach a body to GET", async () => {
    const upstream = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ status: "ok" });
    });
    vi.stubGlobal("fetch", upstream);
    await proxyRequest(new Request("http://web/api/health"), "/health");
    expect(upstream.mock.calls[0]?.[1]?.body).toBeUndefined();
  });

  it("preserves retry-after on domain errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: { code: "BUSY" } }, { status: 503, headers: { "retry-after": "4" } })));
    const response = await proxyRequest(new Request("http://web/api/v1/agent-runs"), "/api/v1/agent-runs");
    expect(response.status).toBe(503);
    expect(response.headers.get("retry-after")).toBe("4");
  });

  it("returns a safe correlated envelope when FastAPI is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("connection refused at internal-host"); }));
    const response = await proxyRequest(new Request("http://web/api/health"), "/health");
    const payload = await response.json();
    expect(response.status).toBe(503);
    expect(payload.error.code).toBe("UPSTREAM_UNAVAILABLE");
    expect(JSON.stringify(payload)).not.toContain("internal-host");
    expect(payload.error.correlation_id).toBeTruthy();
  });

  it("reuses a valid caller correlation ID for a transport failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    const correlationId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const response = await proxyRequest(new Request("http://web/api/health", {
      headers: { "x-correlation-id": correlationId },
    }), "/health");
    expect((await response.json()).error.correlation_id).toBe(correlationId);
  });
});
