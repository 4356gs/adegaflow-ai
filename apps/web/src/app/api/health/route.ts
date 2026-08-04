import { proxyRequest } from "@/lib/server/proxy";

export const dynamic = "force-dynamic";

export function GET(request: Request): Promise<Response> {
  return proxyRequest(request, "/health");
}
