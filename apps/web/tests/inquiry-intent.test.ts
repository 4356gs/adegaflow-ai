import { describe, expect, it, vi } from "vitest";

import {
  MESSAGE_MAX_LENGTH, PENDING_INTENT_KEY, UC001_CUSTOMER_ID, UC001_MESSAGE, createIntent,
  createSubmissionGuard, demoPayload, discardStoredIntent, isTransportError, manualPayload,
  parseIntent, restoreIntent, runIntent, samePayload, serializeIntent, validateMessage,
  type IntentApi,
} from "@/lib/inquiry-intent";
import { ApiError } from "@/lib/api/client";

const inquiry = { id: "inquiry-1", customer_id: null, source: "manual", status: "new", detected_language: null, received_at: "2026-08-04T12:00:00Z" };
const accepted = { agent_run_id: "run-1", inquiry_id: "inquiry-1", status: "queued" as const, current_step: "queued", correlation_id: "corr-1", retry_of_run_id: null, poll_url: "/api/v1/agent-runs/run-1" };

describe("inquiry intent", () => {
  it("normalizes and validates the actual backend bounds", () => {
    expect(manualPayload("  hello  ")).toEqual({ source: "manual", raw_message: "hello", customer_id: null });
    expect(validateMessage(" \n ")).toMatch(/Escribe/);
    expect(validateMessage("x".repeat(MESSAGE_MAX_LENGTH))).toBeNull();
    expect(validateMessage("x".repeat(MESSAGE_MAX_LENGTH + 1))).toMatch(/10.000/);
  });

  it("builds the canonical demo payload without results", () => {
    expect(demoPayload()).toEqual({ source: "demo", raw_message: UC001_MESSAGE, customer_id: UC001_CUSTOMER_ID });
    expect(Object.keys(demoPayload())).toEqual(["source", "raw_message", "customer_id"]);
  });

  it("creates distinct safe keys and round-trips a versioned record", () => {
    const values = ["same", "same", "different"];
    const intent = createIntent(manualPayload("hello"), () => values.shift() ?? "unused");
    expect(intent.inquiryKey).toBe("same");
    expect(intent.runKey).toBe("different");
    expect(parseIntent(serializeIntent(intent))).toEqual(intent);
    expect(parseIntent("not-json")).toBeNull();
    expect(parseIntent(serializeIntent({ ...intent, inquiryKey: "clave con espacios" }))).toBeNull();
    expect(parseIntent(serializeIntent({ ...intent, inquiryKey: "unsafe!" }))).toBeNull();
  });

  it("rejects malformed restored payloads, identifiers and inconsistent stages", () => {
    const base = createIntent(manualPayload("hello"), (() => { let i = 0; return () => `key-${++i}`; })());
    const inquiryId = "11111111-1111-4111-8111-111111111111";
    const runId = "22222222-2222-4222-8222-222222222222";
    expect(parseIntent(serializeIntent({ ...base, payload: { ...base.payload, customer_id: inquiryId } }))).toBeNull();
    expect(parseIntent(JSON.stringify({ ...base, payload: { ...base.payload, extra: true } }))).toBeNull();
    expect(parseIntent(serializeIntent({ ...base, payload: { ...base.payload, raw_message: " hello " } }))).toBeNull();
    expect(parseIntent(serializeIntent({ ...base, stage: "creating_run", inquiryId: "not-a-uuid" }))).toBeNull();
    expect(parseIntent(serializeIntent({ ...base, stage: "creating_run", inquiryId }))).toMatchObject({ inquiryId, stage: "creating_run" });
    expect(parseIntent(serializeIntent({ ...base, stage: "navigating", inquiryId }))).toBeNull();
    expect(parseIntent(serializeIntent({ ...base, stage: "navigating", inquiryId, runId }))).toMatchObject({ runId, stage: "navigating" });
    expect(parseIntent(serializeIntent({ ...base, payload: { source: "demo", raw_message: "arbitrary", customer_id: UC001_CUSTOMER_ID } }))).toBeNull();
  });

  it("restores valid state, removes corrupt state and supports explicit cancellation", () => {
    const intent = createIntent(manualPayload("hello"), () => crypto.randomUUID());
    const storage = { getItem: vi.fn(() => serializeIntent(intent)), removeItem: vi.fn() };
    expect(restoreIntent(storage)).toEqual(intent);
    expect(storage.removeItem).not.toHaveBeenCalled();
    storage.getItem.mockReturnValue("corrupt");
    expect(restoreIntent(storage)).toBeNull();
    expect(storage.removeItem).toHaveBeenCalledWith(PENDING_INTENT_KEY);
    discardStoredIntent(storage);
    expect(storage.removeItem).toHaveBeenLastCalledWith(PENDING_INTENT_KEY);
  });

  it("rejects a synchronous double submission until the active flow releases", () => {
    const guard = createSubmissionGuard();
    expect(guard.acquire()).toBe(true);
    expect(guard.acquire()).toBe(false);
    guard.release();
    expect(guard.acquire()).toBe(true);
  });

  it("compares the frozen source, message and customer", () => {
    expect(samePayload(demoPayload(), demoPayload())).toBe(true);
    expect(samePayload(demoPayload(), manualPayload(UC001_MESSAGE))).toBe(false);
  });

  it("creates inquiry before run with independent keys and persists each accepted stage", async () => {
    const calls: string[] = [];
    const client: IntentApi = {
      createInquiry: vi.fn(async (_payload, key) => { calls.push(`inquiry:${key}`); return inquiry; }),
      createRun: vi.fn(async (id, key) => { calls.push(`run:${id}:${key}`); return accepted; }),
    };
    const intent = createIntent(manualPayload("hello"), (() => { let i = 0; return () => `key-${++i}`; })());
    const persisted: unknown[] = [];
    const result = await runIntent(intent, client, (value) => persisted.push(value), (stage) => calls.push(stage));
    expect(calls).toEqual(["creating_inquiry", "inquiry:key-1", "creating_run", "run:inquiry-1:key-2", "navigating"]);
    expect(result).toMatchObject({ inquiryId: "inquiry-1", runId: "run-1", stage: "navigating" });
    expect(persisted).toHaveLength(2);
  });

  it("resumes at run creation without recreating an accepted inquiry", async () => {
    const client: IntentApi = { createInquiry: vi.fn(), createRun: vi.fn(async () => accepted) };
    const pending = { ...createIntent(manualPayload("hello"), () => crypto.randomUUID()), inquiryId: "inquiry-1", stage: "creating_run" as const };
    await runIntent(pending, client, vi.fn(), vi.fn());
    expect(client.createInquiry).not.toHaveBeenCalled();
    expect(client.createRun).toHaveBeenCalledWith("inquiry-1", pending.runKey);
  });

  it("keeps the same inquiry key when inquiry transport fails", async () => {
    const createInquiry = vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(inquiry);
    const client: IntentApi = { createInquiry, createRun: vi.fn(async () => accepted) };
    const pending = createIntent(manualPayload("hello"), () => crypto.randomUUID());
    await expect(runIntent(pending, client, vi.fn(), vi.fn())).rejects.toThrow("offline");
    await runIntent(pending, client, vi.fn(), vi.fn());
    expect(createInquiry.mock.calls.map((call) => call[1])).toEqual([pending.inquiryKey, pending.inquiryKey]);
  });

  it("keeps the accepted inquiry parent and run key when run transport fails", async () => {
    const createRun = vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(accepted);
    const client: IntentApi = { createInquiry: vi.fn(), createRun };
    const pending = { ...createIntent(manualPayload("hello"), () => crypto.randomUUID()), inquiryId: "inquiry-1", stage: "creating_run" as const };
    await expect(runIntent(pending, client, vi.fn(), vi.fn())).rejects.toThrow("offline");
    const result = await runIntent(pending, client, vi.fn(), vi.fn());
    expect(createRun.mock.calls).toEqual([["inquiry-1", pending.runKey], ["inquiry-1", pending.runKey]]);
    expect(result.runId).toBe("run-1");
  });

  it("navigates a restored accepted run without replaying either POST", async () => {
    const client: IntentApi = { createInquiry: vi.fn(), createRun: vi.fn() };
    const pending = {
      ...createIntent(manualPayload("hello"), () => crypto.randomUUID()),
      inquiryId: "11111111-1111-4111-8111-111111111111",
      runId: "22222222-2222-4222-8222-222222222222",
      stage: "navigating" as const,
    };
    const stages: string[] = [];
    expect(await runIntent(pending, client, vi.fn(), (stage) => stages.push(stage))).toEqual(pending);
    expect(client.createInquiry).not.toHaveBeenCalled();
    expect(client.createRun).not.toHaveBeenCalled();
    expect(stages).toEqual(["navigating"]);
  });

  it("classifies IDEMPOTENCY_CONFLICT as definitive and preserves its safe details", () => {
    const conflict = new ApiError(409, "IDEMPOTENCY_CONFLICT", "Key already used.", "corr-1");
    expect(isTransportError(conflict)).toBe(false);
    expect(conflict).toMatchObject({ message: "Key already used.", correlationId: "corr-1", code: "IDEMPOTENCY_CONFLICT" });
  });

  it("does not rotate or persist new keys after IDEMPOTENCY_CONFLICT", async () => {
    const conflict = new ApiError(409, "IDEMPOTENCY_CONFLICT", "Key already used.", "corr-1");
    const client: IntentApi = { createInquiry: vi.fn(async () => { throw conflict; }), createRun: vi.fn() };
    const pending = createIntent(manualPayload("hello"), () => crypto.randomUUID());
    const persist = vi.fn();
    await expect(runIntent(pending, client, persist, vi.fn())).rejects.toBe(conflict);
    expect(client.createInquiry).toHaveBeenCalledWith(pending.payload, pending.inquiryKey);
    expect(client.createRun).not.toHaveBeenCalled();
    expect(persist).not.toHaveBeenCalled();
    expect(pending).toMatchObject({ inquiryKey: pending.inquiryKey, runKey: pending.runKey });
  });
});
