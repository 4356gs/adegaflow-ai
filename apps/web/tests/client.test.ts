import { afterEach, describe, expect, it, vi } from "vitest";

import { api, apiRequest } from "@/lib/api/client";

afterEach(() => vi.unstubAllGlobals());

describe("typed API client", () => {
  it("creates JSON commands with a stable idempotency key", async () => {
    const fetchMock = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ id: "inquiry-1" }, { status: 201 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.createInquiry({ source: "demo", raw_message: "Hello" }, "key-1");
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe("/api/v1/inquiries");
    expect(new Headers(init?.headers).get("Idempotency-Key")).toBe("key-1");
    expect(init?.body).toBe(JSON.stringify({ source: "demo", raw_message: "Hello" }));
  });

  it("encodes incremental event query parameters", async () => {
    const fetchMock = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ events: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.getEvents("run/unsafe", 7, 25);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/agent-runs/run/unsafe/events?after_sequence=7&limit=25");
  });

  it("raises the safe typed error envelope", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: { code: "RUN_NOT_TERMINAL", message: "Not ready", details: {}, correlation_id: "corr-1" } }, { status: 409 })));
    await expect(api.getResult("run-1")).rejects.toMatchObject({ status: 409, code: "RUN_NOT_TERMINAL", correlationId: "corr-1" });
  });

  it("rejects successful non-JSON responses", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("ok", { status: 200, headers: { "content-type": "text/plain" } })));
    await expect(apiRequest("/api/health")).rejects.toMatchObject({ code: "UNEXPECTED_CONTENT" });
  });

  it("uses a generic safe error for a non-envelope failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("gateway detail", {
      status: 502,
      headers: { "content-type": "text/plain", "x-correlation-id": "corr-2" },
    })));
    await expect(api.health()).rejects.toMatchObject({
      status: 502,
      code: "UNEXPECTED_RESPONSE",
      correlationId: "corr-2",
    });
  });

  it("serializes list filters and omits undefined values", async () => {
    const fetchMock = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ items: [], limit: 10, offset: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.listRuns({ status: "failed", limit: 10, inquiry_id: undefined });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/agent-runs?status=failed&limit=10");
  });

  it("requests the bounded cockpit page exactly", async () => {
    const fetchMock = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ items: [], limit: 20, offset: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.listRuns({ limit: 20, offset: 0 });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/agent-runs?limit=20&offset=0");
  });

  it("does not send a body when none is provided", async () => {
    const fetchMock = vi.fn(async (...args: Parameters<typeof fetch>) => {
      void args;
      return Response.json({ status: "ok" });
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.health();
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBeUndefined();
  });
});
