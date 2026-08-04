import { proxyRequest } from "@/lib/server/proxy";

type RouteContext = { params: Promise<{ path: string[] }> };

export const dynamic = "force-dynamic";

async function forward(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const safePath = path.map((segment) => encodeURIComponent(segment)).join("/");
  return proxyRequest(request, `/api/v1/${safePath}`);
}

export const GET = forward;
export const POST = forward;
