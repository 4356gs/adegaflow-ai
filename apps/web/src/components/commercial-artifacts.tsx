"use client";

import { useState } from "react";
import { emailClipboard, formatDate, formatEuro, proposalClipboard, writePlainText, type ArtifactVm, type QuoteVm } from "@/lib/commercial-result";

function Warnings({ items }: { items: string[] }) { return items.length ? <div className="local-warning"><strong>Advertencias</strong><ul>{items.map((item, i) => <li key={i}>{item}</li>)}</ul></div> : null; }
export function QuoteSnapshot({ quote }: { quote: QuoteVm }) {
  return <div className="deterministic-block"><strong>Snapshot comercial — cálculo determinista</strong><ul>{quote.items.map((line) => <li key={line.productId}>{line.name} ({line.sku}): {line.quantityBottles} botellas · {formatEuro(line.lineTotalCents)}</li>)}</ul><p>Subtotal: <strong>{formatEuro(quote.subtotalCents)}</strong></p></div>;
}
function CopyButton({ label, text }: { label: string; text: string }) {
  const [feedback, setFeedback] = useState("");
  async function copy() {
    setFeedback(await writePlainText(text, navigator.clipboard));
  }
  return <span className="copy-control"><button className="button button-secondary" type="button" onClick={() => void copy()}>{label}</button><span className="copy-feedback" aria-live="polite" role="status">{feedback}</span></span>;
}

export function CommercialArtifacts({ artifacts }: { artifacts: ArtifactVm[] }) {
  const proposals = artifacts.filter((a) => a.kind === "proposal");
  const emails = artifacts.filter((a) => a.kind === "email");
  const incompatible = artifacts.filter((a) => a.kind === "incompatible");
  return <>
    <section className="result-section" aria-labelledby="proposal-title"><h3 id="proposal-title">Propuesta comercial</h3>
      {!proposals.length ? <p className="section-fallback">No se generó en esta ejecución</p> : proposals.map((artifact) => artifact.kind === "proposal" && <article className="artifact-card" key={artifact.value.id}>
        <div className="artifact-heading"><div><p className="provenance ai-narrative">Texto generado por IA — borrador</p><h4>{artifact.value.headline}</h4></div><strong>Borrador — requiere revisión humana</strong></div>
        <p className="artifact-meta">Idioma: {artifact.value.language} · {formatDate(artifact.value.createdAt)} · ID {artifact.value.id.slice(0, 8)}</p>
        <p>{artifact.value.executiveSummary}</p>
        <h5>Posicionamiento</h5><ul>{artifact.value.positioning.map((item) => <li key={item.productId}><strong>{artifact.value.quote.items.find((line) => line.productId === item.productId)?.name ?? item.productId}:</strong> {item.text}</li>)}</ul>
        <h5>Próximos pasos</h5><ul>{artifact.value.nextSteps.map((x, i) => <li key={i}>{x}</li>)}</ul>
        <h5>Preguntas abiertas</h5><ul>{artifact.value.openQuestions.map((x, i) => <li key={i}>{x}</li>)}</ul>
        <Warnings items={artifact.value.warnings}/><QuoteSnapshot quote={artifact.value.quote}/><CopyButton label="Copiar propuesta" text={proposalClipboard(artifact.value)}/>
      </article>)}
    </section>
    <section className="result-section" aria-labelledby="email-title"><h3 id="email-title">Borrador de correo</h3>
      {!emails.length ? <p className="section-fallback">No se generó en esta ejecución</p> : emails.map((artifact) => artifact.kind === "email" && <article className="artifact-card" key={artifact.value.id}>
        <div className="artifact-heading"><div><p className="provenance ai-narrative">Texto generado por IA — borrador</p><h4>{artifact.value.subject}</h4></div><strong>Borrador de correo — no enviado</strong></div>
        <p className="artifact-meta">Destinatario: {artifact.value.recipient.email ?? "Dato pendiente"} · Idioma: {artifact.value.language} · {formatDate(artifact.value.createdAt)} · ID {artifact.value.id.slice(0, 8)}</p>
        <div className="email-body"><p>{artifact.value.introduction}</p><p>{artifact.value.recommendationSummary}</p><ul>{artifact.value.questions.map((x, i) => <li key={i}>{x}</li>)}</ul><p>{artifact.value.nextStep}</p><p>{artifact.value.closing}</p></div>
        <Warnings items={artifact.value.warnings}/><QuoteSnapshot quote={artifact.value.quote}/><div className="copy-actions"><CopyButton label="Copiar asunto" text={artifact.value.subject}/><CopyButton label="Copiar correo" text={emailClipboard(artifact.value)}/></div>
      </article>)}
    </section>
    {incompatible.length ? <section className="result-section" aria-labelledby="other-artifacts-title"><h3 id="other-artifacts-title">Otros artefactos</h3><ul>{incompatible.map((item, i) => <li key={item.kind === "incompatible" ? item.id : i}>Formato no compatible con esta versión{item.kind === "incompatible" ? ` (${item.artifactType})` : ""}</li>)}</ul></section> : null}
  </>;
}
