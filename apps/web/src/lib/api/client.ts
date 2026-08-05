import type {
  AgentRunDetail, AgentRunList, AgentRunStatus, ErrorEnvelope, EventList,
  HealthResponse, InquiryCreate, InquiryDetail, InquiryList, InquiryStatus,
  InquirySummary, MemoryList, OpportunityDetail, RunAccepted, RunResult, UUID,
} from "@/lib/api/types";

type QueryValue = string | number | boolean | null | undefined;
type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  idempotencyKey?: string;
  query?: Record<string, QueryValue>;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly correlationId: string | null,
    public readonly details: Record<string, unknown> = {},
  ) { super(message); this.name = "ApiError"; }
}

function buildPath(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(path, "http://same-origin.invalid");
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) url.searchParams.set(key, String(value));
  }
  return `${url.pathname}${url.search}`;
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!value || typeof value !== "object" || !("error" in value)) return false;
  const error = (value as { error?: unknown }).error;
  return Boolean(error && typeof error === "object" && "code" in error && "message" in error);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  const response = await fetch(buildPath(path, options.query), {
    ...options,
    headers,
    body,
    cache: options.cache ?? "no-store",
  });
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    if (isErrorEnvelope(payload)) {
      throw new ApiError(response.status, payload.error.code, payload.error.message,
        payload.error.correlation_id, payload.error.details);
    }
    throw new ApiError(response.status, "UNEXPECTED_RESPONSE", "The API returned an unexpected response.",
      response.headers.get("x-correlation-id"));
  }
  if (!contentType.includes("application/json")) {
    throw new ApiError(response.status, "UNEXPECTED_CONTENT", "The API returned unsupported content.",
      response.headers.get("x-correlation-id"));
  }
  return payload as T;
}

export const api = {
  health: () => apiRequest<HealthResponse>("/api/health"),
  createInquiry: (input: InquiryCreate, key: string) => apiRequest<InquirySummary>("/api/v1/inquiries", { method: "POST", body: input, idempotencyKey: key }),
  listInquiries: (query: { status?: InquiryStatus; limit?: number; offset?: number } = {}) => apiRequest<InquiryList>("/api/v1/inquiries", { query }),
  getInquiry: (id: UUID) => apiRequest<InquiryDetail>(`/api/v1/inquiries/${id}`),
  createRun: (inquiryId: UUID, key: string) => apiRequest<RunAccepted>(`/api/v1/inquiries/${inquiryId}/agent-runs`, { method: "POST", idempotencyKey: key }),
  listRuns: (query: { status?: AgentRunStatus; inquiry_id?: UUID; limit?: number; offset?: number } = {}) => apiRequest<AgentRunList>("/api/v1/agent-runs", { query }),
  getRun: (id: UUID, signal?: AbortSignal) => apiRequest<AgentRunDetail>(`/api/v1/agent-runs/${id}`, { signal }),
  getEvents: (id: UUID, afterSequence = 0, limit = 100, signal?: AbortSignal) => apiRequest<EventList>(`/api/v1/agent-runs/${id}/events`, { query: { after_sequence: afterSequence, limit }, signal }),
  retryRun: (id: UUID, key: string, signal?: AbortSignal) => apiRequest<RunAccepted>(`/api/v1/agent-runs/${id}/retry`, { method: "POST", idempotencyKey: key, signal }),
  getResult: (id: UUID) => apiRequest<RunResult>(`/api/v1/agent-runs/${id}/result`),
  getOpportunity: (id: UUID) => apiRequest<OpportunityDetail>(`/api/v1/opportunities/${id}`),
  getMemory: (customerId: UUID, limit = 20, offset = 0) => apiRequest<MemoryList>(`/api/v1/customers/${customerId}/memory`, { query: { limit, offset } }),
};
