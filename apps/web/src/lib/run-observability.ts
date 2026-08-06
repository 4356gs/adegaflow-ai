import type {
  AgentRunDetail,
  AgentRunStatus,
  EventList,
  PublicEvent,
  RunAccepted,
  UUID,
} from "@/lib/api/types";

export const POLL_INTERVAL_MS = 1_500;
export const RETRY_INTENT_KEY = "adegaflow.run-retry.v1";
export const EVENT_PAGE_SIZE = 100;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const STATUS_LABELS: Record<AgentRunStatus, string> = {
  queued: "En cola",
  running: "Procesando",
  needs_review: "Listo para revisión",
  completed: "Completado",
  failed: "No se pudo completar",
};

const STEP_LABELS: Record<string, string> = {
  queued: "En cola",
  analyzing: "Analizando consulta",
  retrieving_memory: "Recuperando historial",
  selecting_products: "Seleccionando productos",
  checking_stock: "Verificando stock",
  validating_recommendation: "Validando recomendación",
  calculating_quote: "Calculando cotización",
  generating_artifacts: "Preparando borradores",
  persisting_actions: "Registrando acciones comerciales",
  completed: "Ejecución completada",
  needs_review: "Pendiente de revisión humana",
  failed: "Ejecución fallida",
};

const TOOL_LABELS: Record<string, string> = {
  search_catalog: "Buscar catálogo",
  get_product_details: "Consultar producto",
  check_stock: "Verificar stock",
  retrieve_customer_history: "Recuperar historial",
};

const ACTION_LABELS: Record<string, string> = {
  create_crm_opportunity: "Registrar oportunidad demo",
  create_followup_task: "Programar seguimiento demo",
  save_customer_memory: "Guardar memoria del cliente",
};

type EventDefinition = { label: string; category: string };

const EVENT_DEFINITIONS: Record<string, EventDefinition> = {
  run_created: { label: "Ejecución registrada", category: "Registrado" },
  run_completed: { label: "Ejecución completada", category: "Completado" },
  run_needs_review: { label: "Revisión humana requerida", category: "Revisión" },
  run_failed: { label: "Ejecución fallida", category: "Fallo" },
  run_interrupted: { label: "Ejecución interrumpida", category: "Fallo" },
  dispatch_failed: { label: "No se pudo iniciar el procesamiento", category: "Fallo" },
  analysis_started: { label: "Análisis iniciado", category: "En curso" },
  analysis_reused: { label: "Análisis reutilizado", category: "Reutilizado" },
  analysis_completed: { label: "Análisis completado", category: "Completado" },
  memory_retrieval_started: { label: "Recuperación de historial iniciada", category: "En curso" },
  memory_retrieval_skipped: { label: "Recuperación de historial omitida", category: "Omitido" },
  selection_round_started: { label: "Selección de productos iniciada", category: "En curso" },
  selection_round_completed: { label: "Selección de productos completada", category: "Completado" },
  tool_requested: { label: "Tool solicitada", category: "Solicitada" },
  tool_started: { label: "Tool iniciada", category: "En curso" },
  tool_succeeded: { label: "Tool completada", category: "Completada" },
  tool_failed: { label: "Tool fallida", category: "Fallida" },
  tool_rejected: { label: "Tool rechazada", category: "Rechazada" },
  tool_retry_scheduled: { label: "Nuevo intento de tool programado", category: "Reprogramada" },
  recommendation_draft_requested: { label: "Borrador de recomendación solicitado", category: "En curso" },
  recommendation_draft_received: { label: "Borrador de recomendación recibido", category: "Recibido" },
  recommendation_correction_requested: { label: "Corrección de recomendación solicitada", category: "En curso" },
  recommendation_correction_received: { label: "Corrección de recomendación recibida", category: "Recibido" },
  recommendation_validation_started: { label: "Validación de recomendación iniciada", category: "En curso" },
  recommendation_validated: { label: "Recomendación validada", category: "Validada" },
  recommendation_rejected: { label: "Recomendación rechazada", category: "Rechazada" },
  quote_calculation_started: { label: "Cálculo de cotización iniciado", category: "En curso" },
  quote_calculated: { label: "Cotización calculada", category: "Completada" },
  quote_persisted: { label: "Cotización registrada", category: "Completada" },
  proposal_generation_started: { label: "Preparación de propuesta iniciada", category: "En curso" },
  proposal_received: { label: "Propuesta preparada", category: "Preparada" },
  proposal_rejected: { label: "Propuesta rechazada", category: "Rechazada" },
  proposal_persisted: { label: "Propuesta registrada", category: "Preparada" },
  email_generation_started: { label: "Preparación de correo iniciada", category: "En curso" },
  email_draft_received: { label: "Borrador de correo preparado", category: "Preparado" },
  email_draft_rejected: { label: "Borrador de correo rechazado", category: "Rechazado" },
  email_draft_persisted: { label: "Borrador de correo registrado", category: "Preparado" },
  artifact_generation_partial: { label: "Preparación de borradores parcial", category: "Parcial" },
  internal_actions_started: { label: "Acciones internas iniciadas", category: "En curso" },
  customer_resolution_started: { label: "Resolución de cliente iniciada", category: "En curso" },
  customer_reused: { label: "Cliente demo reutilizado", category: "Reutilizada" },
  customer_created: { label: "Cliente demo registrado", category: "Completada" },
  crm_opportunity_started: { label: "Registro de oportunidad iniciado", category: "En curso" },
  crm_opportunity_persisted: { label: "Oportunidad demo registrada", category: "Completada" },
  followup_task_started: { label: "Programación de seguimiento iniciada", category: "En curso" },
  followup_task_persisted: { label: "Seguimiento demo programado", category: "Completada" },
  customer_memory_started: { label: "Registro de memoria iniciado", category: "En curso" },
  customer_memory_persisted: { label: "Memoria del cliente registrada", category: "Completada" },
  internal_action_reused: { label: "Acción interna reutilizada", category: "Reutilizada" },
  internal_action_rejected: { label: "Acción interna rechazada", category: "Rechazada" },
  internal_actions_rolled_back: { label: "Acciones internas revertidas", category: "Revertida" },
  internal_actions_completed: { label: "Acciones internas completadas", category: "Completada" },
};

export type EventAccumulator = {
  events: PublicEvent[];
  lastSequence: number;
  hydrated: boolean;
};

export type TimelineGroup = { step: string; label: string; events: PublicEvent[] };

export type RetryIntent = {
  version: 1;
  originalRunId: UUID;
  retryKey: UUID;
  stage: "pending_post" | "transport_error" | "accepted";
  acceptedRunId?: UUID;
};

export interface RunReader {
  getRun(id: UUID, signal?: AbortSignal): Promise<AgentRunDetail>;
  getEvents(id: UUID, afterSequence?: number, limit?: number, signal?: AbortSignal): Promise<EventList>;
}

export type RunSynchronization = {
  detail: AgentRunDetail;
  accumulator: EventAccumulator;
  terminal: boolean;
};

export type RunPollingStableState = {
  detail: AgentRunDetail | null;
  accumulator: EventAccumulator;
};

export type RunPollingCoordinator = {
  start(): void;
  retryNow(): void;
  visibilityChanged(): void;
  stop(): void;
};

export type RunPollingOptions = {
  runId: UUID;
  reader: RunReader;
  isHidden: () => boolean;
  onStart: (hasStableDetail: boolean) => void;
  onSuccess: (result: RunSynchronization) => void;
  onError: (error: unknown, stable: RunPollingStableState) => void;
  setTimer?: (callback: () => void, delay: number) => ReturnType<typeof setTimeout>;
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
  queueTask?: (callback: () => void) => void;
  createAbortController?: () => AbortController;
};

export class EventContractError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
    this.name = "EventContractError";
  }
}

export function isValidRunId(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function isTerminalStatus(status: AgentRunStatus): boolean {
  return status === "completed" || status === "needs_review" || status === "failed";
}

export function runStatusLabel(status: AgentRunStatus): string {
  return STATUS_LABELS[status];
}

export function runStepLabel(step: string): string {
  return STEP_LABELS[step] ?? "Paso no reconocido";
}

export function toolLabel(toolName: string): { label: string; known: boolean } {
  return TOOL_LABELS[toolName]
    ? { label: TOOL_LABELS[toolName], known: true }
    : { label: "Tool no reconocida", known: false };
}

export function actionLabel(actionName: string): { label: string; known: boolean } {
  return ACTION_LABELS[actionName]
    ? { label: ACTION_LABELS[actionName], known: true }
    : { label: "Acción interna no reconocida", known: false };
}

export function eventPresentation(event: PublicEvent) {
  const definition = EVENT_DEFINITIONS[event.event_type] ?? {
    label: "Actividad registrada",
    category: "Actividad",
  };
  const toolName = typeof event.payload.tool_name === "string" ? event.payload.tool_name : null;
  const actionName = typeof event.payload.action_name === "string" ? event.payload.action_name : null;
  const errorCode = typeof event.payload.error_code === "string" ? event.payload.error_code : null;
  return {
    ...definition,
    known: event.event_type in EVENT_DEFINITIONS,
    tool: toolName ? { code: toolName, ...toolLabel(toolName) } : null,
    action: actionName ? { code: actionName, ...actionLabel(actionName) } : null,
    errorCode,
  };
}

export function formatRunDate(value: string | null, locale = "es-ES"): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatRunTime(value: string, locale = "es-ES"): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Hora no disponible";
  return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(date);
}

export function abbreviateId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

export function emptyEventAccumulator(): EventAccumulator {
  return { events: [], lastSequence: 0, hydrated: false };
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right));
    return `{${entries.map(([key, child]) => `${JSON.stringify(key)}:${canonicalize(child)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sameEvent(left: PublicEvent, right: PublicEvent): boolean {
  return canonicalize(left) === canonicalize(right);
}

export function applyEventPage(
  accumulator: EventAccumulator,
  page: EventList,
  expectedRunId: UUID,
  afterSequence = accumulator.lastSequence,
  pendingSequence = false,
): EventAccumulator {
  if (page.agent_run_id !== expectedRunId) {
    throw new EventContractError("FOREIGN_RUN", "La respuesta de eventos pertenece a otra ejecución.");
  }
  const expectedLast = page.events.length > 0 ? page.events[page.events.length - 1]!.sequence : afterSequence;
  if (page.last_sequence !== expectedLast) {
    throw new EventContractError("CURSOR_MISMATCH", "El cursor de eventos no coincide con la página recibida.");
  }
  if (page.events.length === 0 && pendingSequence) {
    throw new EventContractError("EMPTY_PENDING_PAGE", "Faltan eventos anunciados por la ejecución.");
  }

  const nextEvents = [...accumulator.events];
  const bySequence = new Map(nextEvents.map((event) => [event.sequence, event]));
  let cursor = accumulator.lastSequence;
  for (const event of page.events) {
    const existing = bySequence.get(event.sequence);
    if (existing) {
      if (!sameEvent(existing, event)) {
        throw new EventContractError("SEQUENCE_CONFLICT", `La secuencia ${event.sequence} contiene datos distintos.`);
      }
      continue;
    }
    if (event.sequence !== cursor + 1) {
      throw new EventContractError("SEQUENCE_GAP", `Se esperaba la secuencia ${cursor + 1} y se recibió ${event.sequence}.`);
    }
    nextEvents.push(event);
    bySequence.set(event.sequence, event);
    cursor = event.sequence;
  }
  if (pendingSequence && cursor <= afterSequence) {
    throw new EventContractError("NON_ADVANCING_PAGE", "La página de eventos no avanzó el cursor anunciado.");
  }
  return { events: nextEvents, lastSequence: cursor, hydrated: true };
}

export function groupConsecutiveEvents(events: PublicEvent[]): TimelineGroup[] {
  return events.reduce<TimelineGroup[]>((groups, event) => {
    const current = groups[groups.length - 1];
    if (current?.step === event.step) {
      current.events.push(event);
    } else {
      groups.push({ step: event.step, label: runStepLabel(event.step), events: [event] });
    }
    return groups;
  }, []);
}

export async function synchronizeRun(
  runId: UUID,
  previous: EventAccumulator,
  reader: RunReader,
  signal?: AbortSignal,
): Promise<RunSynchronization> {
  let detail = await reader.getRun(runId, signal);
  let accumulator = previous;
  let mustReadEvents = !previous.hydrated || accumulator.lastSequence < detail.last_event_sequence;

  while (mustReadEvents) {
    const announcedPending = accumulator.lastSequence < detail.last_event_sequence;
    const page = await reader.getEvents(runId, accumulator.lastSequence, EVENT_PAGE_SIZE, signal);
    accumulator = applyEventPage(accumulator, page, runId, accumulator.lastSequence, announcedPending);

    if (page.terminal && !isTerminalStatus(detail.status)) {
      detail = await reader.getRun(runId, signal);
    }
    mustReadEvents = accumulator.lastSequence < detail.last_event_sequence;
  }

  return {
    detail,
    accumulator,
    terminal: isTerminalStatus(detail.status) && accumulator.lastSequence >= detail.last_event_sequence,
  };
}

export function createRunPollingCoordinator({
  runId,
  reader,
  isHidden,
  onStart,
  onSuccess,
  onError,
  setTimer = (callback, delay) => setTimeout(callback, delay),
  clearTimer = (timer) => clearTimeout(timer),
  queueTask = (callback) => queueMicrotask(callback),
  createAbortController = () => new AbortController(),
}: RunPollingOptions): RunPollingCoordinator {
  let disposed = false;
  let inFlight = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let controller: AbortController | null = null;
  let resumeAfterFlight = false;
  let accumulator = emptyEventAccumulator();
  let currentDetail: AgentRunDetail | null = null;

  const cancelTimer = () => {
    if (timer !== null) clearTimer(timer);
    timer = null;
  };

  const schedule = () => {
    cancelTimer();
    if (disposed || isHidden() || (currentDetail && isTerminalStatus(currentDetail.status))) return;
    timer = setTimer(() => void synchronize(), POLL_INTERVAL_MS);
  };

  const synchronize = async () => {
    if (disposed || inFlight || isHidden()) return;
    cancelTimer();
    inFlight = true;
    controller = createAbortController();
    onStart(currentDetail !== null);
    let scheduleNext = false;

    try {
      const result = await synchronizeRun(runId, accumulator, reader, controller.signal);
      if (disposed) return;
      accumulator = result.accumulator;
      currentDetail = result.detail;
      onSuccess(result);
      scheduleNext = !result.terminal;
    } catch (error) {
      if (disposed || (error instanceof DOMException && error.name === "AbortError")) return;
      onError(error, { detail: currentDetail, accumulator });
    } finally {
      inFlight = false;
      controller = null;
      const resumeNow = resumeAfterFlight;
      resumeAfterFlight = false;
      if (resumeNow && scheduleNext && !disposed && !isHidden()) {
        void synchronize();
      } else if (scheduleNext) {
        schedule();
      }
    }
  };

  return {
    start() {
      if (!disposed) queueTask(() => void synchronize());
    },
    retryNow() {
      void synchronize();
    },
    visibilityChanged() {
      if (isHidden()) {
        resumeAfterFlight = false;
        cancelTimer();
      } else if (inFlight) {
        resumeAfterFlight = true;
      } else {
        void synchronize();
      }
    },
    stop() {
      disposed = true;
      resumeAfterFlight = false;
      cancelTimer();
      controller?.abort();
    },
  };
}

export function createRetryIntent(originalRunId: UUID, randomUUID: () => UUID = () => crypto.randomUUID()): RetryIntent {
  return { version: 1, originalRunId, retryKey: randomUUID(), stage: "pending_post" };
}

export function acceptRetryIntent(intent: RetryIntent, accepted: RunAccepted): RetryIntent {
  return { ...intent, stage: "accepted", acceptedRunId: accepted.agent_run_id };
}

export function markRetryTransportError(intent: RetryIntent): RetryIntent {
  return { ...intent, stage: "transport_error" };
}

export function serializeRetryIntent(intent: RetryIntent): string {
  return JSON.stringify(intent);
}

export function restoreRetryIntent(storage: Pick<Storage, "getItem">, runId?: UUID): RetryIntent | null {
  const raw = storage.getItem(RETRY_INTENT_KEY);
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<RetryIntent>;
    const valid = value.version === 1
      && typeof value.originalRunId === "string"
      && isValidRunId(value.originalRunId)
      && typeof value.retryKey === "string"
      && isValidRunId(value.retryKey)
      && (value.stage === "pending_post" || value.stage === "transport_error" || value.stage === "accepted")
      && (value.acceptedRunId === undefined || (typeof value.acceptedRunId === "string" && isValidRunId(value.acceptedRunId)));
    if (!valid || (runId && value.originalRunId !== runId && value.acceptedRunId !== runId)) return null;
    return value as RetryIntent;
  } catch {
    return null;
  }
}

export function discardRetryIntent(storage: Pick<Storage, "removeItem">): void {
  storage.removeItem(RETRY_INTENT_KEY);
}

export function runStateMessage(status: AgentRunStatus): string {
  const messages: Record<AgentRunStatus, string> = {
    queued: "La ejecución está en cola y comenzará en cuanto haya capacidad disponible.",
    running: "El agente está procesando la consulta. La actividad se actualiza automáticamente.",
    completed: "La ejecución terminó correctamente. Los entregables se incorporarán en el siguiente bloque.",
    needs_review: "La ejecución produjo un resultado útil que requiere revisión humana antes de continuar.",
    failed: "La ejecución no pudo completarse. Revisa el error seguro y las opciones disponibles.",
  };
  return messages[status];
}
