import { describe, expect, it } from "vitest";

import { getApiBaseUrl, isDemoMode } from "@/lib/server/config";

describe("server configuration", () => {
  it("uses a local server-only default", () => {
    expect(getApiBaseUrl({}).href).toBe("http://127.0.0.1:8000/");
  });
  it("accepts an HTTP service URL and removes trailing paths", () => {
    expect(getApiBaseUrl({ FASTAPI_BASE_URL: "http://api:8000/" }).href).toBe("http://api:8000/");
  });
  it("rejects non-HTTP protocols", () => {
    expect(() => getApiBaseUrl({ FASTAPI_BASE_URL: "file:///tmp/api" })).toThrow(/HTTP/);
  });
  it("rejects malformed URLs without exposing their value", () => {
    expect(() => getApiBaseUrl({ FASTAPI_BASE_URL: "not a url" })).toThrow(
      "FASTAPI_BASE_URL must be an absolute HTTP(S) URL.",
    );
  });
  it("keeps demo mode enabled by default", () => {
    expect(isDemoMode({})).toBe(true);
    expect(isDemoMode({ DEMO_MODE: "false" })).toBe(false);
  });
  it("normalizes case when reading demo mode", () => {
    expect(isDemoMode({ DEMO_MODE: "TRUE" })).toBe(true);
  });
});
