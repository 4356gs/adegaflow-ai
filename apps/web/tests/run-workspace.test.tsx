import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi, type Mock } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));

import {
  RunWorkspaceView,
  createRunRetryCoordinator,
  type RetryUiState,
  type WorkspaceSnapshot,
} from "@/components/run-workspace";
import { ApiError } from "@/lib/api/client";
import type { AgentRunDetail, PublicEvent, RunAccepted } from "@/lib/api/types";
import { RETRY_INTENT_KEY, restoreRetryIntent, serializeRetryIntent, type RetryIntent } from "@/lib/run-observability";

const RUN_ID = "22222222-2222-4222-8222-222222222222";
const ORIGINAL_ID = "11111111-1111-4111-8111-111111111111";
const RETRY_KEY = "44444444-4444-4444-8444-444444444444";
const ACCEPTED_ID = "66666666-6666-4666-8666-666666666666";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: vi.fn((key: string) => values.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => { values.set(key, value); }),
    removeItem: vi.fn((key: string) => { values.delete(key); }),
  };
}

function accepted(): RunAccepted {
  return {
    agent_run_id: ACCEPTED_ID,
    inquiry_id: "33333333-3333-4333-8333-333333333333",
    status: "queued",
    current_step: "queued",
    correlation_id: "77777777-7777-4777-8777-777777777777",
    retry_of_run_id: RUN_ID,
    poll_url: `/api/v1/agent-runs/${ACCEPTED_ID}`,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
}

function detail(overrides: Partial<AgentRunDetail> = {}): AgentRunDetail {
  return {
    id: RUN_ID,
    inquiry_id: "33333333-3333-4333-8333-333333333333",
    retry_of_run_id: null,
    correlation_id: "55555555-5555-4555-8555-555555555555",
    status: "running",
    current_step: "checking_stock",
    started_at: "2026-08-05T12:00:00Z",
    completed_at: null,
    model: "model-not-rendered",
    prompt_versions: { secret: "not-rendered" },
    error: null,
    retryable: false,
    references: { quote_id: null, proposal_id: null, email_draft_id: null, opportunity_id: null, followup_task_id: null },
    last_event_sequence: 0,
    events_url: "/events-not-rendered",
    result_url: "/result-not-rendered",
    ...overrides,
  };
}

function event(sequence: number, overrides: Partial<PublicEvent> = {}): PublicEvent {
  return { sequence, event_type: "tool_started", step: "checking_stock", payload: { tool_name: "check_stock" }, created_at: "2026-08-05T12:00:01Z", ...overrides };
}

function snapshot(detailValue = detail(), events: PublicEvent[] = []): WorkspaceSnapshot {
  return { detail: detailValue, events, syncing: false, readIssue: null };
}

function view(snapshotValue: WorkspaceSnapshot | null, retryState: RetryUiState = { kind: "idle" }, initialIssue: Parameters<typeof RunWorkspaceView>[0]["initialIssue"] = null) {
  return renderToStaticMarkup(
    <RunWorkspaceView
      runId={RUN_ID}
      snapshot={snapshotValue}
      initialIssue={initialIssue}
      retryState={retryState}
      retryRevoked={false}
      onReadRetry={vi.fn()}
      onRetry={vi.fn()}
      onDiscardRetry={vi.fn()}
    />,
  );
}

describe("run workspace route states", () => {
  it("announces loading without fictitious data", () => {
    const html = view(null);
    expect(html).toContain("Cargando ejecución");
    expect(html).toContain('role="status"');
    expect(html).not.toContain(RUN_ID);
  });

  it("distinguishes not found from recoverable initial reads", () => {
    const notFound = view(null, { kind: "idle" }, { kind: "not_found", message: "No existe", correlationId: "corr-404" });
    expect(notFound).toContain("Ejecución no encontrada");
    expect(notFound).not.toContain("Volver a intentar actualización");
    const failedRead = view(null, { kind: "idle" }, { kind: "request", message: "Temporal", correlationId: "corr-1" });
    expect(failedRead).toContain("Volver a intentar actualización");
    expect(failedRead).toContain("corr-1");
  });

  it.each([
    ["queued", "En cola"], ["running", "Procesando"], ["completed", "Completado"],
    ["needs_review", "Listo para revisión"], ["failed", "No se pudo completar"],
  ] as const)("renders a textual %s state", (status, label) => {
    const html = view(snapshot(detail({ status, current_step: status })));
    expect(html).toContain(label);
    expect(html).toContain(`status-${status}`);
  });

  it("shows support metadata and links a retry to the immutable original", () => {
    const html = view(snapshot(detail({ retry_of_run_id: ORIGINAL_ID, completed_at: "2026-08-05T12:10:00Z" })));
    expect(html).toContain(RUN_ID);
    expect(html).toContain("Correlation ID");
    expect(html).toContain('href="/runs/11111111-1111-4111-8111-111111111111"');
    expect(html).toContain("Reintento de");
    expect(html).not.toContain("model-not-rendered");
    expect(html).not.toContain("result-not-rendered");
  });

  it("keeps the valid timeline while a later read is degraded", () => {
    const degraded = snapshot(detail(), [event(1)]);
    degraded.readIssue = { kind: "contract", message: "Incomplete", correlationId: null };
    const html = view(degraded);
    expect(html).toContain("La timeline necesita resincronizarse");
    expect(html).toContain("Verificar stock");
    expect(html).toContain("Volver a intentar actualización");
  });
});

describe("timeline presentation", () => {
  it("renders tools, internal actions, unknown events and safe technical details", () => {
    const html = view(snapshot(detail({ last_event_sequence: 3 }), [
      event(1),
      event(2, { event_type: "followup_task_persisted", step: "persisting_actions", payload: { action_name: "create_followup_task" } }),
      event(3, { event_type: "future_event", step: "future_step", payload: { tool_name: "future_tool", hidden_output: "never render" } }),
    ]));
    expect(html).toContain("Tool");
    expect(html).toContain("Verificar stock");
    expect(html).toContain("Acción interna");
    expect(html).toContain("Programar seguimiento demo");
    expect(html).toContain("Actividad registrada");
    expect(html).toContain("Paso no reconocido");
    expect(html).toContain("future_step");
    expect(html).toContain("future_tool");
    expect(html).not.toContain("never render");
    expect(html).not.toContain("hidden_output");
  });

  it("uses semantic ordered lists, timestamps and disclosures", () => {
    const html = view(snapshot(detail({ last_event_sequence: 1 }), [event(1)]));
    expect(html).toContain("<ol");
    expect(html).toContain("<time");
    expect(html).toContain("<details");
    expect(html).toContain("Detalles técnicos");
  });

  it("renders a clear empty timeline", () => {
    expect(view(snapshot())).toContain("Todavía no hay actividad registrada");
  });
});

describe("retry controls", () => {
  const failed = detail({ status: "failed", current_step: "failed", retryable: true, error: { code: "MODEL_TIMEOUT", message: "Tiempo agotado" } });
  const intent = { version: 1 as const, originalRunId: RUN_ID, retryKey: RETRY_KEY, stage: "transport_error" as const };

  it("appears only for failed and backend-retryable runs", () => {
    expect(view(snapshot(failed))).toContain("Crear nuevo intento");
    expect(view(snapshot({ ...failed, retryable: false }))).not.toContain("Crear nuevo intento");
    expect(view(snapshot(detail({ status: "needs_review", retryable: true })))).not.toContain("Crear nuevo intento");
  });

  it("renders only the safe run error and correlation reference", () => {
    const html = view(snapshot(failed));
    expect(html).toContain("MODEL_TIMEOUT");
    expect(html).toContain("Tiempo agotado");
    expect(html).toContain(failed.correlation_id);
    expect(html).not.toContain("stack");
  });

  it("requires explicit continuation for a recovered or uncertain intent", () => {
    const recovered = view(snapshot(failed), { kind: "recovered", intent });
    expect(recovered).toContain("Solo continuará cuando lo confirmes");
    expect(recovered).toContain("Continuar reintento");
    const uncertain = view(snapshot(failed), { kind: "transport_error", intent, message: "Incierto", correlationId: null });
    expect(uncertain).toContain("misma clave");
    expect(uncertain).toContain("Continuar reintento");
  });

  it("blocks the command while submitting and allows explicit discard after a definitive conflict", () => {
    const submitting = view(snapshot(failed), { kind: "submitting", intent });
    expect(submitting).toContain("disabled");
    expect(submitting).toContain("Creando nuevo intento");
    const conflict = view(snapshot(failed), { kind: "definitive_error", intent, message: "Conflicto", correlationId: "corr-conflict" });
    expect(conflict).toContain("Descartar esta intención");
    expect(conflict).not.toContain(">Crear nuevo intento<");
  });

  it("blocks a new retry while another run owns the global intent", () => {
    const foreignIntent: RetryIntent = { ...intent, originalRunId: ORIGINAL_ID };
    const html = view(snapshot(failed), { kind: "blocked_by_other_run", intent: foreignIntent });
    expect(html).toContain("Hay otro reintento pendiente");
    expect(html).toContain(`href="/runs/${ORIGINAL_ID}"`);
    expect(html).toContain("Descartar esta intención");
    expect(html).not.toContain(">Crear nuevo intento<");
  });
});

describe("retry coordinator integration", () => {
  type RetryRun = (id: string, key: string, signal?: AbortSignal) => Promise<RunAccepted>;

  function coordinator(overrides: {
    storage?: ReturnType<typeof memoryStorage>;
    retryRun?: Mock<RetryRun>;
    navigate?: Mock<(path: string) => void>;
    onState?: Mock<(state: RetryUiState) => void>;
    onRevoked?: Mock<() => void>;
    onRefresh?: Mock<() => void>;
  } = {}) {
    const storage = overrides.storage ?? memoryStorage();
    const retryRun = overrides.retryRun ?? vi.fn<RetryRun>(async () => accepted());
    const navigate = overrides.navigate ?? vi.fn<(path: string) => void>();
    const onState = overrides.onState ?? vi.fn<(state: RetryUiState) => void>();
    const onRevoked = overrides.onRevoked ?? vi.fn<() => void>();
    const onRefresh = overrides.onRefresh ?? vi.fn<() => void>();
    return {
      storage,
      retryRun,
      navigate,
      onState,
      onRevoked,
      onRefresh,
      value: createRunRetryCoordinator({
        runId: RUN_ID,
        storage,
        retryRun,
        navigate,
        onState,
        onRevoked,
        onRefresh,
        randomUUID: () => RETRY_KEY,
      }),
    };
  }

  it("detects a foreign global intent and cannot overwrite it without explicit discard", async () => {
    const storage = memoryStorage();
    const foreignIntent: RetryIntent = {
      version: 1,
      originalRunId: ORIGINAL_ID,
      retryKey: RETRY_KEY,
      stage: "transport_error",
    };
    storage.setItem(RETRY_INTENT_KEY, serializeRetryIntent(foreignIntent));
    const subject = coordinator({ storage });

    subject.value.restore();
    expect(subject.onState).toHaveBeenLastCalledWith({ kind: "blocked_by_other_run", intent: foreignIntent });
    await subject.value.execute();
    expect(subject.retryRun).not.toHaveBeenCalled();
    expect(restoreRetryIntent(storage)).toEqual(foreignIntent);

    subject.value.discard();
    expect(restoreRetryIntent(storage)).toBeNull();
    expect(subject.onState).toHaveBeenLastCalledWith({ kind: "idle" });
  });

  it("uses a synchronous guard so a double click creates one logical POST", async () => {
    const pending = deferred<RunAccepted>();
    const retryRun = vi.fn(() => pending.promise);
    const subject = coordinator({ retryRun });

    const first = subject.value.execute();
    const second = subject.value.execute();
    expect(retryRun).toHaveBeenCalledTimes(1);
    expect(retryRun).toHaveBeenCalledWith(RUN_ID, RETRY_KEY, expect.any(AbortSignal));

    pending.resolve(accepted());
    await Promise.all([first, second]);
    expect(subject.navigate).toHaveBeenCalledOnce();
    expect(subject.navigate).toHaveBeenCalledWith(`/runs/${ACCEPTED_ID}`);
    expect(restoreRetryIntent(subject.storage)).toMatchObject({
      originalRunId: RUN_ID,
      retryKey: RETRY_KEY,
      stage: "accepted",
      acceptedRunId: ACCEPTED_ID,
    });
  });

  it("continues a transport failure with the same idempotency key", async () => {
    const retryRun = vi.fn()
      .mockRejectedValueOnce(new TypeError("network"))
      .mockResolvedValueOnce(accepted());
    const subject = coordinator({ retryRun });

    await subject.value.execute();
    const uncertain = subject.onState.mock.calls.at(-1)?.[0] as RetryUiState;
    expect(uncertain).toMatchObject({ kind: "transport_error", intent: { retryKey: RETRY_KEY } });
    if (uncertain.kind !== "transport_error") throw new Error("Expected transport error state");

    await subject.value.execute(uncertain.intent);
    expect(retryRun.mock.calls.map((call) => call[1])).toEqual([RETRY_KEY, RETRY_KEY]);
    expect(subject.navigate).toHaveBeenCalledWith(`/runs/${ACCEPTED_ID}`);
  });

  it("opens an already accepted retry without issuing another POST", async () => {
    const intent: RetryIntent = {
      version: 1,
      originalRunId: RUN_ID,
      retryKey: RETRY_KEY,
      stage: "accepted",
      acceptedRunId: ACCEPTED_ID,
    };
    const storage = memoryStorage();
    storage.setItem(RETRY_INTENT_KEY, serializeRetryIntent(intent));
    const subject = coordinator({ storage });

    subject.value.restore();
    expect(subject.onState).toHaveBeenLastCalledWith({ kind: "recovered", intent });
    await subject.value.execute(intent);
    expect(subject.retryRun).not.toHaveBeenCalled();
    expect(subject.navigate).toHaveBeenCalledWith(`/runs/${ACCEPTED_ID}`);
  });

  it("revokes retry and refreshes detail when the backend reports RUN_NOT_RETRYABLE", async () => {
    const retryRun = vi.fn(async () => {
      throw new ApiError(409, "RUN_NOT_RETRYABLE", "No retry", "corr-revoked");
    });
    const subject = coordinator({ retryRun });

    await subject.value.execute();
    expect(subject.onState).toHaveBeenLastCalledWith(expect.objectContaining({
      kind: "definitive_error",
      correlationId: "corr-revoked",
    }));
    expect(subject.onRevoked).toHaveBeenCalledOnce();
    expect(subject.onRefresh).toHaveBeenCalledOnce();
    expect(restoreRetryIntent(subject.storage)).toBeNull();
  });
});
