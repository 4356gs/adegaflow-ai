"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { RunTimeline } from "@/components/run-timeline";
import { ApiError, api } from "@/lib/api/client";
import type { AgentRunDetail, PublicEvent, UUID } from "@/lib/api/types";
import {
  POLL_INTERVAL_MS,
  RETRY_INTENT_KEY,
  EventContractError,
  abbreviateId,
  acceptRetryIntent,
  createRetryIntent,
  discardRetryIntent,
  emptyEventAccumulator,
  formatRunDate,
  isTerminalStatus,
  markRetryTransportError,
  restoreRetryIntent,
  runStateMessage,
  runStatusLabel,
  runStepLabel,
  serializeRetryIntent,
  synchronizeRun,
  type RetryIntent,
} from "@/lib/run-observability";

type ReadIssue = {
  kind: "not_found" | "request" | "contract";
  message: string;
  correlationId: string | null;
};

export type WorkspaceSnapshot = {
  detail: AgentRunDetail;
  events: PublicEvent[];
  syncing: boolean;
  readIssue: ReadIssue | null;
};

export type RetryUiState =
  | { kind: "idle" }
  | { kind: "recovered"; intent: RetryIntent }
  | { kind: "submitting"; intent: RetryIntent }
  | { kind: "transport_error"; intent: RetryIntent; message: string; correlationId: string | null }
  | { kind: "definitive_error"; intent: RetryIntent; message: string; correlationId: string | null };

function requestIssue(error: unknown): ReadIssue {
  if (error instanceof EventContractError) {
    return { kind: "contract", message: "La actividad recibida está incompleta o fuera de orden.", correlationId: null };
  }
  if (error instanceof ApiError) {
    return {
      kind: error.status === 404 && error.code === "AGENT_RUN_NOT_FOUND" ? "not_found" : "request",
      message: error.message,
      correlationId: error.correlationId,
    };
  }
  return { kind: "request", message: "No se pudo actualizar la ejecución.", correlationId: null };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function RunWorkspace({ runId }: { runId: UUID }) {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot | null>(null);
  const [initialIssue, setInitialIssue] = useState<ReadIssue | null>(null);
  const [retryState, setRetryState] = useState<RetryUiState>({ kind: "idle" });
  const [retryRevoked, setRetryRevoked] = useState(false);
  const synchronizeRef = useRef<() => void>(() => undefined);
  const retryGuardRef = useRef(false);
  const retryControllerRef = useRef<AbortController | null>(null);
  const retryErrorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const restored = restoreRetryIntent(sessionStorage, runId);
    if (!restored) return;
    if (restored.acceptedRunId === runId) {
      discardRetryIntent(sessionStorage);
      return;
    }
    queueMicrotask(() => {
      if (!cancelled) setRetryState({ kind: "recovered", intent: restored });
    });
    return () => { cancelled = true; };
  }, [runId]);

  useEffect(() => {
    let disposed = false;
    let inFlight = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;
    let resumeAfterFlight = false;
    let accumulator = emptyEventAccumulator();
    let currentDetail: AgentRunDetail | null = null;

    const clearTimer = () => {
      if (timer) clearTimeout(timer);
      timer = null;
    };

    const schedule = () => {
      clearTimer();
      if (disposed || document.hidden || (currentDetail && isTerminalStatus(currentDetail.status))) return;
      timer = setTimeout(() => void synchronize(), POLL_INTERVAL_MS);
    };

    const synchronize = async () => {
      if (disposed || inFlight || document.hidden) return;
      clearTimer();
      inFlight = true;
      controller = new AbortController();
      if (currentDetail) {
        setSnapshot((value) => value ? { ...value, syncing: true } : value);
      } else {
        setInitialIssue(null);
      }
      let scheduleNext = false;
      try {
        const result = await synchronizeRun(runId, accumulator, api, controller.signal);
        if (disposed) return;
        accumulator = result.accumulator;
        currentDetail = result.detail;
        setSnapshot({ detail: result.detail, events: accumulator.events, syncing: false, readIssue: null });
        setInitialIssue(null);
        setRetryRevoked(false);

        const stored = restoreRetryIntent(sessionStorage, runId);
        if (stored?.acceptedRunId === runId) {
          discardRetryIntent(sessionStorage);
          setRetryState({ kind: "idle" });
        }
        scheduleNext = !result.terminal;
      } catch (error) {
        if (disposed || isAbortError(error)) return;
        const issue = requestIssue(error);
        if (currentDetail) {
          setSnapshot({ detail: currentDetail, events: accumulator.events, syncing: false, readIssue: issue });
        } else {
          setInitialIssue(issue);
        }
      } finally {
        inFlight = false;
        controller = null;
        const resumeNow = resumeAfterFlight;
        resumeAfterFlight = false;
        if (resumeNow && scheduleNext && !disposed && !document.hidden) {
          void synchronize();
        } else if (scheduleNext) {
          schedule();
        }
      }
    };

    synchronizeRef.current = () => void synchronize();
    const onVisibilityChange = () => {
      if (document.hidden) {
        resumeAfterFlight = false;
        clearTimer();
      } else if (inFlight) {
        resumeAfterFlight = true;
      } else {
        void synchronize();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    queueMicrotask(() => void synchronize());

    return () => {
      disposed = true;
      clearTimer();
      controller?.abort();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      synchronizeRef.current = () => undefined;
    };
  }, [runId]);

  useEffect(() => () => retryControllerRef.current?.abort(), []);

  useEffect(() => {
    if (retryState.kind !== "transport_error" && retryState.kind !== "definitive_error") return;
    const frame = requestAnimationFrame(() => retryErrorRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [retryState.kind]);

  const persistRetry = useCallback((intent: RetryIntent) => {
    sessionStorage.setItem(RETRY_INTENT_KEY, serializeRetryIntent(intent));
  }, []);

  const executeRetry = useCallback(async (existing?: RetryIntent) => {
    if (retryGuardRef.current) return;
    retryGuardRef.current = true;
    let intent = existing ?? createRetryIntent(runId);
    persistRetry(intent);
    setRetryState({ kind: "submitting", intent });
    if (intent.acceptedRunId) {
      router.replace(`/runs/${intent.acceptedRunId}`);
      retryGuardRef.current = false;
      return;
    }

    retryControllerRef.current = new AbortController();
    try {
      const accepted = await api.retryRun(runId, intent.retryKey, retryControllerRef.current.signal);
      intent = acceptRetryIntent(intent, accepted);
      persistRetry(intent);
      router.replace(`/runs/${accepted.agent_run_id}`);
    } catch (error) {
      if (isAbortError(error)) return;
      const message = error instanceof ApiError ? error.message : "La respuesta del nuevo intento es incierta.";
      const correlationId = error instanceof ApiError ? error.correlationId : null;
      if (error instanceof ApiError && (error.code === "IDEMPOTENCY_CONFLICT" || error.code === "RUN_NOT_RETRYABLE")) {
        setRetryState({ kind: "definitive_error", intent, message, correlationId });
        if (error.code === "RUN_NOT_RETRYABLE") {
          discardRetryIntent(sessionStorage);
          setRetryRevoked(true);
          synchronizeRef.current();
        }
      } else {
        intent = markRetryTransportError(intent);
        persistRetry(intent);
        setRetryState({ kind: "transport_error", intent, message, correlationId });
      }
    } finally {
      retryControllerRef.current = null;
      retryGuardRef.current = false;
    }
  }, [persistRetry, router, runId]);

  const discardRetry = useCallback(() => {
    discardRetryIntent(sessionStorage);
    setRetryState({ kind: "idle" });
  }, []);

  return (
    <RunWorkspaceView
      runId={runId}
      snapshot={snapshot}
      initialIssue={initialIssue}
      retryState={retryState}
      retryRevoked={retryRevoked}
      retryErrorRef={retryErrorRef}
      onReadRetry={() => synchronizeRef.current()}
      onRetry={(intent) => void executeRetry(intent)}
      onDiscardRetry={discardRetry}
    />
  );
}

export function RunWorkspaceView({
  runId,
  snapshot,
  initialIssue,
  retryState,
  retryRevoked,
  retryErrorRef,
  onReadRetry,
  onRetry,
  onDiscardRetry,
}: {
  runId: UUID;
  snapshot: WorkspaceSnapshot | null;
  initialIssue: ReadIssue | null;
  retryState: RetryUiState;
  retryRevoked: boolean;
  retryErrorRef?: React.RefObject<HTMLDivElement | null>;
  onReadRetry: () => void;
  onRetry: (intent?: RetryIntent) => void;
  onDiscardRetry: () => void;
}) {
  if (!snapshot) {
    if (initialIssue?.kind === "not_found") {
      return (
        <section className="narrow-page" aria-labelledby="run-title">
          <p className="eyebrow">Workspace de ejecución</p>
          <h1 id="run-title">Ejecución no encontrada</h1>
          <div className="state-card error-card" role="alert">
            <p>{initialIssue.message}</p>
            {initialIssue.correlationId ? <p className="correlation">Referencia: {initialIssue.correlationId}</p> : null}
          </div>
          <Link className="button button-secondary" href="/">Volver al cockpit</Link>
        </section>
      );
    }
    if (initialIssue) {
      return (
        <section className="narrow-page" aria-labelledby="run-title">
          <p className="eyebrow">Workspace de ejecución</p>
          <h1 id="run-title">No pudimos cargar la ejecución</h1>
          <div className="state-card error-card" role="alert">
            <p>{initialIssue.message}</p>
            {initialIssue.correlationId ? <p className="correlation">Referencia: {initialIssue.correlationId}</p> : null}
            <button className="button button-secondary" type="button" onClick={onReadRetry}>Volver a intentar actualización</button>
          </div>
          <Link className="button button-quiet" href="/">Volver al cockpit</Link>
        </section>
      );
    }
    return <section className="narrow-page" aria-labelledby="run-title" aria-busy="true"><p className="eyebrow">Workspace de ejecución</p><h1 id="run-title">Cargando ejecución</h1><p className="state-card" role="status">Consultando estado y actividad real…</p></section>;
  }

  const { detail, events, syncing, readIssue } = snapshot;
  const startedAt = formatRunDate(detail.started_at);
  const completedAt = formatRunDate(detail.completed_at);
  const retryAllowed = detail.status === "failed" && detail.retryable && !retryRevoked;
  const activeRetryIntent = retryState.kind === "idle" ? undefined : retryState.intent;
  const retryBusy = retryState.kind === "submitting";
  const retryError = retryState.kind === "transport_error" || retryState.kind === "definitive_error" ? retryState : null;

  return (
    <div className="run-workspace">
      <Link className="back-link" href="/">← Volver al cockpit</Link>
      <header className="run-header" aria-labelledby="run-title">
        <div className="run-title-row">
          <div>
            <p className="eyebrow">Workspace de ejecución</p>
            <h1 id="run-title">Ejecución {abbreviateId(runId)}</h1>
          </div>
          <span className={`status status-${detail.status} run-status`}><span aria-hidden="true">●</span>{runStatusLabel(detail.status)}</span>
        </div>
        <p className="run-step"><span>Paso actual</span><strong>{runStepLabel(detail.current_step)}</strong>{runStepLabel(detail.current_step) === "Paso no reconocido" ? <code>{detail.current_step}</code> : null}</p>
        <dl className="run-metadata">
          <div><dt>Inicio</dt><dd><time dateTime={detail.started_at}>{startedAt}</time></dd></div>
          {detail.completed_at ? <div><dt>Finalización</dt><dd><time dateTime={detail.completed_at}>{completedAt}</time></dd></div> : null}
          <div className="full-id"><dt>Identificador del run</dt><dd><code>{runId}</code></dd></div>
        </dl>
        {detail.retry_of_run_id ? <Link className="retry-origin-link" href={`/runs/${detail.retry_of_run_id}`} aria-label={`Abrir ejecución original ${detail.retry_of_run_id}`}>Reintento de {abbreviateId(detail.retry_of_run_id)} →</Link> : null}
        <details className="support-details"><summary>Detalles de soporte</summary><dl><div><dt>Correlation ID</dt><dd><code>{detail.correlation_id}</code></dd></div></dl></details>
      </header>

      <section className={`run-state-panel state-${detail.status}`} aria-labelledby="run-state-title">
        <div>
          <p className="eyebrow">Estado</p>
          <h2 id="run-state-title">{runStatusLabel(detail.status)}</h2>
          <p>{runStateMessage(detail.status)}</p>
          {detail.error ? <div className="safe-run-error"><strong>{detail.error.code}</strong><p>{detail.error.message}</p><p className="correlation">Referencia: {detail.correlation_id}</p></div> : null}
        </div>
        {syncing && !readIssue ? <span className="sync-state" role="status">Actualizando…</span> : null}
      </section>

      {readIssue ? (
        <div className="state-card warning-card" role="alert">
          <h2>{readIssue.kind === "contract" ? "La timeline necesita resincronizarse" : "La actualización se interrumpió"}</h2>
          <p>{readIssue.message} Los datos ya confirmados permanecen visibles.</p>
          {readIssue.correlationId ? <p className="correlation">Referencia: {readIssue.correlationId}</p> : null}
          <button className="button button-secondary" type="button" onClick={onReadRetry}>Volver a intentar actualización</button>
        </div>
      ) : null}

      {retryState.kind === "recovered" ? <div className="recovery-note" role="status">Hay un nuevo intento pendiente. Solo continuará cuando lo confirmes y conservará la misma clave idempotente.</div> : null}
      {retryError ? (
        <div className="state-card error-card retry-error" role="alert" tabIndex={-1} ref={retryErrorRef}>
          <h2>{retryState.kind === "transport_error" ? "No pudimos confirmar el nuevo intento" : "No se puede continuar este intento"}</h2>
          <p>{retryError.message}</p>
          {retryError.correlationId ? <p className="correlation">Referencia: {retryError.correlationId}</p> : null}
          {retryState.kind === "transport_error" ? <p>Continúa con la misma clave para evitar duplicados.</p> : <button className="text-button" type="button" onClick={onDiscardRetry}>Descartar esta intención</button>}
        </div>
      ) : null}
      {retryAllowed && retryState.kind !== "definitive_error" ? (
        <div className="retry-panel">
          <div><h2>Crear un nuevo intento</h2><p>El intento actual permanecerá intacto y el nuevo quedará enlazado a este run.</p></div>
          <button className="button button-primary" type="button" disabled={retryBusy} aria-disabled={retryBusy} onClick={() => onRetry(activeRetryIntent)}>
            {retryBusy ? "Creando nuevo intento…" : activeRetryIntent?.acceptedRunId ? "Abrir nuevo intento" : activeRetryIntent ? "Continuar reintento" : "Crear nuevo intento"}
          </button>
        </div>
      ) : null}

      <div className="sr-only" aria-live="polite" role="status">{syncing ? "Actualizando ejecución" : `Estado: ${runStatusLabel(detail.status)}`}</div>
      <RunTimeline events={events} />
    </div>
  );
}
