import type { Metadata } from "next";
import Link from "next/link";

import { RunWorkspace } from "@/components/run-workspace";
import { isValidRunId } from "@/lib/run-observability";

export const metadata: Metadata = { title: "Ejecución" };

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  if (isValidRunId(runId)) return <RunWorkspace key={runId} runId={runId} />;
  return (
    <section className="narrow-page" aria-labelledby="run-title">
      <p className="eyebrow">Workspace de ejecución</p>
      <h1 id="run-title">Identificador no válido</h1>
      <p className="state-card error-card" role="alert">La dirección no contiene un identificador de ejecución válido. No se realizó ninguna consulta.</p>
      <Link className="button button-secondary" href="/">Volver al cockpit</Link>
    </section>
  );
}
