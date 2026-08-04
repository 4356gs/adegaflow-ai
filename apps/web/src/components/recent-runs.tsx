"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api/client";
import type { AgentRunSummary } from "@/lib/api/types";
import { presentRun } from "@/lib/runs";

export type RunsLoadState =
  | { kind: "loading" }
  | { kind: "ready"; runs: AgentRunSummary[] }
  | { kind: "error"; message: string; correlationId: string | null };

export function RecentRuns() {
  const [state, setState] = useState<RunsLoadState>({ kind: "loading" });

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const response = await api.listRuns({ limit: 20, offset: 0 });
      setState({ kind: "ready", runs: response.items.slice(0, 20) });
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof ApiError ? error.message : "No se pudieron cargar las ejecuciones.",
        correlationId: error instanceof ApiError ? error.correlationId : null,
      });
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => { void load(); });
  }, [load]);

  return <RecentRunsView state={state} onRetry={() => void load()} />;
}

export function RecentRunsView({ state, onRetry }: { state: RunsLoadState; onRetry: () => void }) {
  return (
    <section className="runs-panel" aria-labelledby="recent-runs-title" aria-busy={state.kind === "loading"}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Actividad</p>
          <h2 id="recent-runs-title">Ejecuciones recientes</h2>
        </div>
        {state.kind === "ready" && state.runs.length > 0 ? <span className="muted">Últimas {state.runs.length}</span> : null}
      </div>
      {state.kind === "loading" ? <p className="state-card" role="status">Cargando ejecuciones recientes…</p> : null}
      {state.kind === "error" ? (
        <div className="state-card error-card" role="alert">
          <h3>No pudimos cargar las ejecuciones</h3>
          <p>{state.message}</p>
          {state.correlationId ? <p className="correlation">Referencia: {state.correlationId}</p> : null}
          <button className="button button-secondary" type="button" onClick={onRetry}>Volver a intentar</button>
        </div>
      ) : null}
      {state.kind === "ready" && state.runs.length === 0 ? (
        <div className="state-card">
          <h3>Aún no hay ejecuciones</h3>
          <p>Crea una consulta para iniciar el primer trabajo del agente.</p>
          <Link className="button button-secondary" href="/inquiries/new">Crear primera consulta</Link>
        </div>
      ) : null}
      {state.kind === "ready" && state.runs.length > 0 ? (
        <ul className="run-list">
          {state.runs.map((run) => {
            const item = presentRun(run);
            return (
              <li className="run-card" key={run.id}>
                <div className="run-card-main">
                  <span className={`status status-${run.status}`}><span aria-hidden="true">●</span>{item.status}</span>
                  <h3>{item.company}</h3>
                  <dl>
                    <div><dt>Mercado</dt><dd>{item.market}</dd></div>
                    <div><dt>Recibida</dt><dd>{item.receivedAt}</dd></div>
                  </dl>
                </div>
                <Link className="run-link" href={`/runs/${run.id}`} aria-label={`Abrir ejecución de ${item.company}`}>Abrir ejecución <span aria-hidden="true">→</span></Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
