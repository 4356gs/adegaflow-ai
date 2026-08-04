import type { AgentRunStatus, AgentRunSummary } from "@/lib/api/types";

const STATUS_LABELS: Record<AgentRunStatus, string> = {
  queued: "En cola",
  running: "Procesando",
  needs_review: "Listo para revisión",
  completed: "Completado",
  failed: "No se pudo completar",
};

export function runStatusLabel(status: AgentRunStatus): string {
  return STATUS_LABELS[status];
}

export function formatReceivedAt(value: string, locale = "es-ES"): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function presentRun(run: AgentRunSummary, locale = "es-ES") {
  return {
    company: run.company_name ?? "Empresa no disponible",
    market: run.market ?? "Mercado no disponible",
    receivedAt: formatReceivedAt(run.received_at, locale),
    status: runStatusLabel(run.status),
  };
}
