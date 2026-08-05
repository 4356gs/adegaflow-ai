import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AgentRunDetail, EventList, PublicEvent } from "@/lib/api/types";
import {
  EVENT_PAGE_SIZE,
  POLL_INTERVAL_MS,
  EventContractError,
  abbreviateId,
  acceptRetryIntent,
  actionLabel,
  applyEventPage,
  createRunPollingCoordinator,
  createRetryIntent,
  emptyEventAccumulator,
  eventPresentation,
  formatRunDate,
  groupConsecutiveEvents,
  isTerminalStatus,
  isValidRunId,
  markRetryTransportError,
  restoreRetryIntent,
  runStatusLabel,
  runStepLabel,
  serializeRetryIntent,
  synchronizeRun,
  toolLabel,
} from "@/lib/run-observability";

const RUN_ID = "22222222-2222-4222-8222-222222222222";
const INQUIRY_ID = "11111111-1111-4111-8111-111111111111";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function flushAsync(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

function event(sequence: number, overrides: Partial<PublicEvent> = {}): PublicEvent {
  return {
    sequence,
    event_type: "analysis_started",
    step: "analyzing",
    payload: {},
    created_at: `2026-08-05T12:00:${String(sequence % 60).padStart(2, "0")}Z`,
    ...overrides,
  };
}

function page(events: PublicEvent[], overrides: Partial<EventList> = {}): EventList {
  return {
    agent_run_id: RUN_ID,
    events,
    last_sequence: events.at(-1)?.sequence ?? 0,
    terminal: false,
    ...overrides,
  };
}

function detail(overrides: Partial<AgentRunDetail> = {}): AgentRunDetail {
  return {
    id: RUN_ID,
    inquiry_id: INQUIRY_ID,
    retry_of_run_id: null,
    correlation_id: "33333333-3333-4333-8333-333333333333",
    status: "running",
    current_step: "analyzing",
    started_at: "2026-08-05T12:00:00Z",
    completed_at: null,
    model: "model",
    prompt_versions: {},
    error: null,
    retryable: false,
    references: { quote_id: null, proposal_id: null, email_draft_id: null, opportunity_id: null, followup_task_id: null },
    last_event_sequence: 0,
    events_url: `/api/v1/agent-runs/${RUN_ID}/events`,
    result_url: `/api/v1/agent-runs/${RUN_ID}/result`,
    ...overrides,
  };
}

describe("run presentation", () => {
  it("uses the approved 1.5 second polling delay", () => {
    expect(POLL_INTERVAL_MS).toBe(1_500);
  });

  it("validates only canonical UUIDs", () => {
    expect(isValidRunId(RUN_ID)).toBe(true);
    expect(isValidRunId("run/unsafe")).toBe(false);
    expect(isValidRunId("22222222-2222-0222-8222-222222222222")).toBe(false);
  });

  it.each([
    ["queued", "En cola"], ["running", "Procesando"], ["needs_review", "Listo para revisión"],
    ["completed", "Completado"], ["failed", "No se pudo completar"],
  ] as const)("maps status %s", (status, label) => expect(runStatusLabel(status)).toBe(label));

  it("maps all known steps and preserves an unknown code outside the label", () => {
    const steps = ["queued", "analyzing", "retrieving_memory", "selecting_products", "checking_stock", "validating_recommendation", "calculating_quote", "generating_artifacts", "persisting_actions", "completed", "needs_review", "failed"];
    expect(steps.map(runStepLabel)).not.toContain("Paso no reconocido");
    expect(runStepLabel("future_step")).toBe("Paso no reconocido");
  });

  it("maps the public tools and internal actions without confusing their families", () => {
    expect(["search_catalog", "get_product_details", "check_stock", "retrieve_customer_history"].map(toolLabel).every((item) => item.known)).toBe(true);
    expect(["create_crm_opportunity", "create_followup_task", "save_customer_memory"].map(actionLabel).every((item) => item.known)).toBe(true);
    expect(toolLabel("future_tool")).toEqual({ label: "Tool no reconocida", known: false });
    expect(actionLabel("future_action")).toEqual({ label: "Acción interna no reconocida", known: false });
  });

  it("presents known, unknown, tool and action events from allowlisted fields only", () => {
    expect(eventPresentation(event(1)).known).toBe(true);
    expect(eventPresentation(event(2, { event_type: "future_event" }))).toMatchObject({ label: "Actividad registrada", known: false });
    expect(eventPresentation(event(3, { payload: { tool_name: "check_stock", secret: "not-used" } }))).toMatchObject({ tool: { label: "Verificar stock", known: true } });
    expect(eventPresentation(event(4, { payload: { action_name: "create_followup_task" } }))).toMatchObject({ action: { label: "Programar seguimiento demo", known: true } });
  });

  it("formats safe date and compact identifier fallbacks", () => {
    expect(formatRunDate(null)).toBeNull();
    expect(formatRunDate("not-a-date")).toBe("Fecha no disponible");
    expect(abbreviateId(RUN_ID)).toBe("22222222…2222");
  });

  it("classifies terminality from run status only", () => {
    expect(["completed", "needs_review", "failed"].every((status) => isTerminalStatus(status as AgentRunDetail["status"]))).toBe(true);
    expect(isTerminalStatus("running")).toBe(false);
  });
});

describe("event accumulator integrity", () => {
  it("advances through contiguous pages", () => {
    const first = applyEventPage(emptyEventAccumulator(), page([event(1), event(2)]), RUN_ID);
    const second = applyEventPage(first, page([event(3)], { last_sequence: 3 }), RUN_ID);
    expect(second.events.map((item) => item.sequence)).toEqual([1, 2, 3]);
    expect(second.lastSequence).toBe(3);
  });

  it("ignores identical replay even when payload property order changes", () => {
    const original = event(1, { payload: { tool_name: "check_stock", model_round: 1 } });
    const replay = event(1, { payload: { model_round: 1, tool_name: "check_stock" } });
    const first = applyEventPage(emptyEventAccumulator(), page([original]), RUN_ID);
    const repeated = applyEventPage(first, page([replay], { last_sequence: 1 }), RUN_ID, 0);
    expect(repeated.events).toHaveLength(1);
  });

  it.each([
    ["FOREIGN_RUN", page([event(1)], { agent_run_id: INQUIRY_ID })],
    ["CURSOR_MISMATCH", page([event(1)], { last_sequence: 7 })],
    ["SEQUENCE_GAP", page([event(2)], { last_sequence: 2 })],
  ])("rejects %s", (code, response) => {
    expect(() => applyEventPage(emptyEventAccumulator(), response, RUN_ID)).toThrowError(EventContractError);
    try { applyEventPage(emptyEventAccumulator(), response, RUN_ID); } catch (error) { expect(error).toMatchObject({ code }); }
  });

  it("rejects conflicting replay", () => {
    const first = applyEventPage(emptyEventAccumulator(), page([event(1)]), RUN_ID);
    expect(() => applyEventPage(first, page([event(1, { event_type: "analysis_completed" })]), RUN_ID, 0)).toThrowError(expect.objectContaining({ code: "SEQUENCE_CONFLICT" }));
  });

  it("rejects an empty page when detail announced pending events", () => {
    expect(() => applyEventPage(emptyEventAccumulator(), page([]), RUN_ID, 0, true)).toThrowError(expect.objectContaining({ code: "EMPTY_PENDING_PAGE" }));
  });

  it("rejects an identical replay that cannot advance an announced cursor", () => {
    const first = applyEventPage(emptyEventAccumulator(), page([event(1)]), RUN_ID);
    expect(() => applyEventPage(first, page([event(1)]), RUN_ID, 1, true)).toThrowError(expect.objectContaining({ code: "NON_ADVANCING_PAGE" }));
  });

  it("groups only consecutive occurrences of the same step", () => {
    const groups = groupConsecutiveEvents([event(1), event(2), event(3, { step: "checking_stock" }), event(4)]);
    expect(groups.map((group) => [group.step, group.events.length])).toEqual([["analyzing", 2], ["checking_stock", 1], ["analyzing", 1]]);
  });
});

describe("incremental synchronization", () => {
  it("hydrates detail first and requests events from zero even when empty", async () => {
    const calls: string[] = [];
    const reader = {
      getRun: vi.fn(async () => { calls.push("detail"); return detail(); }),
      getEvents: vi.fn(async (_id: string, cursor: number, limit: number) => { calls.push(`events:${cursor}:${limit}`); return page([]); }),
    };
    const result = await synchronizeRun(RUN_ID, emptyEventAccumulator(), reader);
    expect(calls).toEqual(["detail", `events:0:${EVENT_PAGE_SIZE}`]);
    expect(result.terminal).toBe(false);
  });

  it("drains more than one bounded page sequentially", async () => {
    const allEvents = Array.from({ length: 101 }, (_, index) => event(index + 1));
    const reader = {
      getRun: vi.fn(async () => detail({ last_event_sequence: 101 })),
      getEvents: vi.fn(async (_id: string, cursor: number) => page(allEvents.slice(cursor, cursor + 100), { last_sequence: Math.min(cursor + 100, 101) })),
    };
    const result = await synchronizeRun(RUN_ID, emptyEventAccumulator(), reader);
    expect(reader.getEvents.mock.calls.map((call) => call[1])).toEqual([0, 100]);
    expect(result.accumulator.lastSequence).toBe(101);
  });

  it("refreshes an active detail when the event endpoint reports terminal", async () => {
    const getRun = vi.fn()
      .mockResolvedValueOnce(detail({ last_event_sequence: 1 }))
      .mockResolvedValueOnce(detail({ status: "completed", current_step: "completed", completed_at: "2026-08-05T12:01:00Z", last_event_sequence: 1 }));
    const reader = { getRun, getEvents: vi.fn(async () => page([event(1)], { terminal: true })) };
    const result = await synchronizeRun(RUN_ID, emptyEventAccumulator(), reader);
    expect(getRun).toHaveBeenCalledTimes(2);
    expect(result.terminal).toBe(true);
  });

  it("does not fetch an already hydrated terminal timeline again", async () => {
    const reader = {
      getRun: vi.fn(async () => detail({ status: "needs_review", current_step: "needs_review", last_event_sequence: 1 })),
      getEvents: vi.fn(),
    };
    const result = await synchronizeRun(RUN_ID, { events: [event(1)], lastSequence: 1, hydrated: true }, reader);
    expect(reader.getEvents).not.toHaveBeenCalled();
    expect(result.terminal).toBe(true);
  });
});

describe("polling coordinator integration", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("waits 1.5 seconds after a completed cycle before starting the next one", async () => {
    const reader = {
      getRun: vi.fn(async () => detail()),
      getEvents: vi.fn(async () => page([])),
    };
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader,
      isHidden: () => false,
      onStart: vi.fn(),
      onSuccess: vi.fn(),
      onError: vi.fn(),
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    expect(reader.getRun).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS - 1);
    expect(reader.getRun).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    await flushAsync();
    expect(reader.getRun).toHaveBeenCalledTimes(2);
    coordinator.stop();
  });

  it("never overlaps cycles and resumes immediately after an in-flight visibility change", async () => {
    const secondDetail = deferred<AgentRunDetail>();
    const getRun = vi.fn()
      .mockResolvedValueOnce(detail())
      .mockImplementationOnce(() => secondDetail.promise)
      .mockResolvedValue(detail());
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader: { getRun, getEvents: vi.fn(async () => page([])) },
      isHidden: () => false,
      onStart: vi.fn(),
      onSuccess: vi.fn(),
      onError: vi.fn(),
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(getRun).toHaveBeenCalledTimes(2);

    coordinator.visibilityChanged();
    expect(getRun).toHaveBeenCalledTimes(2);
    secondDetail.resolve(detail());
    await flushAsync();
    expect(getRun).toHaveBeenCalledTimes(3);
    coordinator.stop();
  });

  it("pauses while hidden and resumes with the last confirmed cursor", async () => {
    let hidden = false;
    const getRun = vi.fn()
      .mockResolvedValueOnce(detail({ last_event_sequence: 1 }))
      .mockResolvedValueOnce(detail({ last_event_sequence: 2 }));
    const getEvents = vi.fn(async (_id: string, cursor: number) => (
      cursor === 0 ? page([event(1)]) : page([event(2)], { last_sequence: 2 })
    ));
    const successes: number[][] = [];
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader: { getRun, getEvents },
      isHidden: () => hidden,
      onStart: vi.fn(),
      onSuccess: (result) => successes.push(result.accumulator.events.map((item) => item.sequence)),
      onError: vi.fn(),
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    hidden = true;
    coordinator.visibilityChanged();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2);
    expect(getRun).toHaveBeenCalledTimes(1);

    hidden = false;
    coordinator.visibilityChanged();
    await flushAsync();
    expect(getEvents.mock.calls.map((call) => call[1])).toEqual([0, 1]);
    expect(successes.at(-1)).toEqual([1, 2]);
    coordinator.stop();
  });

  it("stops automatic polling after a fully drained terminal run", async () => {
    const reader = {
      getRun: vi.fn(async () => detail({ status: "completed", current_step: "completed", last_event_sequence: 1 })),
      getEvents: vi.fn(async () => page([event(1)], { terminal: true })),
    };
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader,
      isHidden: () => false,
      onStart: vi.fn(),
      onSuccess: vi.fn(),
      onError: vi.fn(),
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    expect(reader.getRun).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
    coordinator.stop();
  });

  it("aborts the active request and removes its timer when stopped", async () => {
    let observedSignal: AbortSignal | undefined;
    const getRun = vi.fn((_id: string, signal?: AbortSignal) => new Promise<AgentRunDetail>((_resolve, reject) => {
      observedSignal = signal;
      signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    const onError = vi.fn();
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader: { getRun, getEvents: vi.fn() },
      isHidden: () => false,
      onStart: vi.fn(),
      onSuccess: vi.fn(),
      onError,
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    coordinator.stop();
    await flushAsync();
    expect(observedSignal?.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    expect(onError).not.toHaveBeenCalled();
  });

  it("recovers manually from the same cursor after a read failure", async () => {
    const getRun = vi.fn()
      .mockResolvedValueOnce(detail({ last_event_sequence: 1 }))
      .mockResolvedValue(detail({ last_event_sequence: 2 }));
    let cursorOneAttempts = 0;
    const getEvents = vi.fn(async (_id: string, cursor: number) => {
      if (cursor === 0) return page([event(1)]);
      cursorOneAttempts += 1;
      if (cursorOneAttempts === 1) throw new TypeError("temporary");
      return page([event(2)], { last_sequence: 2 });
    });
    const onError = vi.fn();
    const onSuccess = vi.fn();
    const coordinator = createRunPollingCoordinator({
      runId: RUN_ID,
      reader: { getRun, getEvents },
      isHidden: () => false,
      onStart: vi.fn(),
      onSuccess,
      onError,
      queueTask: (callback) => callback(),
    });

    coordinator.start();
    await flushAsync();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    await flushAsync();
    expect(onError).toHaveBeenCalledWith(expect.any(TypeError), expect.objectContaining({
      accumulator: expect.objectContaining({ lastSequence: 1 }),
    }));
    expect(vi.getTimerCount()).toBe(0);

    coordinator.retryNow();
    await flushAsync();
    expect(getEvents.mock.calls.map((call) => call[1])).toEqual([0, 1, 1]);
    expect(onSuccess.mock.calls.at(-1)?.[0].accumulator.lastSequence).toBe(2);
    coordinator.stop();
  });
});

describe("retry intent", () => {
  const RETRY_KEY = "44444444-4444-4444-8444-444444444444";
  const ACCEPTED_ID = "55555555-5555-4555-8555-555555555555";

  it("creates one stable key and preserves it through transport and acceptance", () => {
    const intent = createRetryIntent(RUN_ID, () => RETRY_KEY);
    const uncertain = markRetryTransportError(intent);
    const accepted = acceptRetryIntent(uncertain, { agent_run_id: ACCEPTED_ID } as never);
    expect(uncertain.retryKey).toBe(RETRY_KEY);
    expect(accepted).toMatchObject({ retryKey: RETRY_KEY, stage: "accepted", acceptedRunId: ACCEPTED_ID });
  });

  it("serializes and restores only valid, scoped records", () => {
    const intent = createRetryIntent(RUN_ID, () => RETRY_KEY);
    const storage = { getItem: vi.fn(() => serializeRetryIntent(intent)) };
    expect(restoreRetryIntent(storage, RUN_ID)).toEqual(intent);
    expect(restoreRetryIntent(storage, ACCEPTED_ID)).toBeNull();
    expect(restoreRetryIntent({ getItem: () => "{bad" }, RUN_ID)).toBeNull();
  });
});
