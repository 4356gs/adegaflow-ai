import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Ejecución" };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const valid = UUID_PATTERN.test(runId);
  return <section className="narrow-page" aria-labelledby="run-title"><p className="eyebrow">Workspace de ejecución</p><h1 id="run-title">{valid ? "Ejecución aceptada" : "Identificador no válido"}</h1>{valid ? <><p className="lede">El agente aceptó el trabajo. La observabilidad de esta ejecución se incorpora en el Bloque 3.</p><dl className="identifier-card"><dt>Identificador del run</dt><dd><code>{runId}</code></dd></dl></> : <p className="state-card error-card">La dirección no contiene un identificador de ejecución válido.</p>}<Link className="button button-secondary" href="/">Volver al cockpit</Link></section>;
}
