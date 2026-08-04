import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server/proxy", () => ({ proxyRequest: vi.fn(async (_request: Request, path: string) => Response.json({ path })) }));

import { GET as getHealth } from "@/app/api/health/route";
import { GET as getApi, POST as postApi } from "@/app/api/v1/[...path]/route";

describe("route adapters", () => {
  it("maps /api/health to the unversioned backend health", async () => {
    expect(await (await getHealth(new Request("http://web/api/health"))).json()).toEqual({ path: "/health" });
  });
  it.each([["GET", getApi], ["POST", postApi]])("forwards %s under the versioned boundary", async (_method, handler) => {
    const response = await handler(new Request("http://web/api/v1/agent-runs"), { params: Promise.resolve({ path: ["agent-runs"] }) });
    expect(await response.json()).toEqual({ path: "/api/v1/agent-runs" });
  });
  it("encodes decoded route segments before proxying", async () => {
    const response = await getApi(new Request("http://web/api/v1/inquiries"), { params: Promise.resolve({ path: ["inquiries", "a/b"] }) });
    expect(await response.json()).toEqual({ path: "/api/v1/inquiries/a%2Fb" });
  });
});
