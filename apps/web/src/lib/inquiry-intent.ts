import type { InquiryCreate, InquirySummary, RunAccepted, UUID } from "@/lib/api/types";

export const MESSAGE_MAX_LENGTH = 10_000;
export const UC001_MESSAGE = "We need 600 bottles of Albariño for specialised wine shops in Germany. Recommend two references.";
export const UC001_CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1";
export const PENDING_INTENT_KEY = "adegaflow.pending-inquiry-intent";

export type IntentStage = "creating_inquiry" | "creating_run" | "navigating";

export interface PendingIntent {
  version: 1;
  payload: InquiryCreate;
  inquiryKey: string;
  runKey: string;
  stage: IntentStage;
  inquiryId?: UUID;
  runId?: UUID;
}

interface SessionStorageLike {
  getItem(key: string): string | null;
  removeItem(key: string): void;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const IDEMPOTENCY_KEY_PATTERN = /^[A-Za-z0-9._:/+\-=]{1,160}$/;

export function normalizeMessage(message: string): string { return message.trim(); }

export function validateMessage(message: string): string | null {
  const normalized = normalizeMessage(message);
  if (!normalized) return "Escribe una consulta antes de continuar.";
  if (normalized.length > MESSAGE_MAX_LENGTH) return `El mensaje no puede superar ${MESSAGE_MAX_LENGTH.toLocaleString("es-ES")} caracteres.`;
  return null;
}

export function manualPayload(message: string): InquiryCreate {
  return { source: "manual", raw_message: normalizeMessage(message), customer_id: null };
}

export function demoPayload(): InquiryCreate {
  return { source: "demo", raw_message: UC001_MESSAGE, customer_id: UC001_CUSTOMER_ID };
}

export function samePayload(left: InquiryCreate, right: InquiryCreate): boolean {
  return left.source === right.source && left.raw_message === right.raw_message && (left.customer_id ?? null) === (right.customer_id ?? null);
}

export function createIntent(payload: InquiryCreate, randomUUID: () => string = () => crypto.randomUUID()): PendingIntent {
  const inquiryKey = randomUUID();
  let runKey = randomUUID();
  while (runKey === inquiryKey) runKey = randomUUID();
  return { version: 1, payload, inquiryKey, runKey, stage: "creating_inquiry" };
}

export function serializeIntent(intent: PendingIntent): string { return JSON.stringify(intent); }

export function parseIntent(value: string | null): PendingIntent | null {
  if (!value) return null;
  try {
    const candidate: unknown = JSON.parse(value);
    if (!candidate || typeof candidate !== "object") return null;
    const record = candidate as Partial<PendingIntent>;
    if (record.version !== 1 || !record.payload || typeof record.payload !== "object" || typeof record.inquiryKey !== "string" || typeof record.runKey !== "string") return null;
    if (!(["creating_inquiry", "creating_run", "navigating"] as const).includes(record.stage as IntentStage)) return null;
    if (record.inquiryKey === record.runKey || !IDEMPOTENCY_KEY_PATTERN.test(record.inquiryKey) || !IDEMPOTENCY_KEY_PATTERN.test(record.runKey)) return null;
    if ((record.payload.source !== "manual" && record.payload.source !== "demo") || typeof record.payload.raw_message !== "string") return null;
    if (validateMessage(record.payload.raw_message) || normalizeMessage(record.payload.raw_message) !== record.payload.raw_message) return null;
    if (Object.keys(record.payload).sort().join(",") !== "customer_id,raw_message,source") return null;
    if (record.payload.source === "manual" && record.payload.customer_id !== null) return null;
    if (record.payload.source === "demo" && (record.payload.customer_id !== UC001_CUSTOMER_ID || record.payload.raw_message !== UC001_MESSAGE)) return null;
    const hasInquiryId = typeof record.inquiryId === "string" && UUID_PATTERN.test(record.inquiryId);
    const hasRunId = typeof record.runId === "string" && UUID_PATTERN.test(record.runId);
    if (record.inquiryId !== undefined && !hasInquiryId) return null;
    if (record.runId !== undefined && !hasRunId) return null;
    if (record.stage === "creating_inquiry" && (record.inquiryId !== undefined || record.runId !== undefined)) return null;
    if (record.stage === "creating_run" && (!hasInquiryId || record.runId !== undefined)) return null;
    if (record.stage === "navigating" && (!hasInquiryId || !hasRunId)) return null;
    return record as PendingIntent;
  } catch { return null; }
}

export function restoreIntent(storage: SessionStorageLike): PendingIntent | null {
  const serialized = storage.getItem(PENDING_INTENT_KEY);
  const intent = parseIntent(serialized);
  if (serialized !== null && !intent) storage.removeItem(PENDING_INTENT_KEY);
  return intent;
}

export function discardStoredIntent(storage: Pick<SessionStorageLike, "removeItem">): void {
  storage.removeItem(PENDING_INTENT_KEY);
}

export interface SubmissionGuard { acquire(): boolean; release(): void }

export function createSubmissionGuard(): SubmissionGuard {
  let active = false;
  return {
    acquire() { if (active) return false; active = true; return true; },
    release() { active = false; },
  };
}

export function isTransportError(error: unknown): boolean {
  return error instanceof TypeError || (typeof error === "object" && error !== null && "code" in error && ["UPSTREAM_UNAVAILABLE", "UNEXPECTED_RESPONSE", "UNEXPECTED_CONTENT"].includes(String(error.code)));
}

export interface IntentApi {
  createInquiry(payload: InquiryCreate, key: string): Promise<InquirySummary>;
  createRun(inquiryId: UUID, key: string): Promise<RunAccepted>;
}

export async function runIntent(
  initial: PendingIntent,
  client: IntentApi,
  persist: (intent: PendingIntent) => void,
  onStage: (stage: IntentStage) => void,
): Promise<PendingIntent> {
  let intent = initial;
  if (intent.stage === "navigating" && intent.inquiryId && intent.runId) {
    onStage("navigating");
    return intent;
  }
  let inquiryId = intent.inquiryId;
  if (!inquiryId) {
    onStage("creating_inquiry");
    inquiryId = (await client.createInquiry(intent.payload, intent.inquiryKey)).id;
    intent = { ...intent, inquiryId, stage: "creating_run" };
    persist(intent);
  }
  onStage("creating_run");
  const accepted = await client.createRun(inquiryId, intent.runKey);
  intent = { ...intent, inquiryId, runId: accepted.agent_run_id, stage: "navigating" };
  persist(intent);
  onStage("navigating");
  return intent;
}
