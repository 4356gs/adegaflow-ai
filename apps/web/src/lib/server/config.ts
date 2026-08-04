const DEFAULT_API_URL = "http://127.0.0.1:8000";

type Environment = Readonly<Record<string, string | undefined>>;

export function getApiBaseUrl(environment: Environment = process.env): URL {
  const raw = environment.FASTAPI_BASE_URL?.trim() || DEFAULT_API_URL;
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("FASTAPI_BASE_URL must be an absolute HTTP(S) URL.");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("FASTAPI_BASE_URL must use HTTP or HTTPS.");
  }
  parsed.pathname = parsed.pathname.replace(/\/$/, "");
  parsed.search = "";
  parsed.hash = "";
  return parsed;
}

export function isDemoMode(environment: Environment = process.env): boolean {
  return (environment.DEMO_MODE ?? "true").toLowerCase() === "true";
}
