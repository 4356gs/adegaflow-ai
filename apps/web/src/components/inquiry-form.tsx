"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, api } from "@/lib/api/client";
import {
  MESSAGE_MAX_LENGTH, PENDING_INTENT_KEY, UC001_MESSAGE, createIntent, createSubmissionGuard, demoPayload,
  discardStoredIntent, isTransportError, manualPayload, restoreIntent, runIntent, samePayload,
  serializeIntent, validateMessage,
  type PendingIntent,
} from "@/lib/inquiry-intent";
import type { InquiryCreate } from "@/lib/api/types";

type Progress = "idle" | "creating_inquiry" | "creating_run" | "navigating";
type FormError = { message: string; correlationId: string | null; retryable: boolean };

function payloadFor(message: string, demo: boolean): InquiryCreate {
  return demo && message === UC001_MESSAGE ? demoPayload() : manualPayload(message);
}

export function InquiryForm() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [isDemo, setIsDemo] = useState(false);
  const [progress, setProgress] = useState<Progress>("idle");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formError, setFormError] = useState<FormError | null>(null);
  const [recovered, setRecovered] = useState(false);
  const intentRef = useRef<PendingIntent | null>(null);
  const submissionGuard = useRef(createSubmissionGuard());
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const pending = restoreIntent(sessionStorage);
    if (!pending) return;
    intentRef.current = pending;
    queueMicrotask(() => {
      setMessage(pending.payload.raw_message);
      setIsDemo(pending.payload.source === "demo");
      setRecovered(true);
    });
  }, []);

  function persist(intent: PendingIntent) {
    intentRef.current = intent;
    sessionStorage.setItem(PENDING_INTENT_KEY, serializeIntent(intent));
  }

  function discardIntent() {
    intentRef.current = null;
    discardStoredIntent(sessionStorage);
    setRecovered(false);
  }

  function editMessage(value: string) {
    if (intentRef.current || isDemo) discardIntent();
    setMessage(value);
    setIsDemo(false);
    setValidationError(null);
    setFormError(null);
  }

  function loadDemo() {
    discardIntent();
    setMessage(UC001_MESSAGE);
    setIsDemo(true);
    setValidationError(null);
    setFormError(null);
    textareaRef.current?.focus();
  }

  async function execute(intent: PendingIntent) {
    try {
      intent = await runIntent(intent, api, persist, setProgress);
      discardStoredIntent(sessionStorage);
      intentRef.current = null;
      router.replace(`/runs/${intent.runId}`);
    } catch (error) {
      const retryable = isTransportError(error);
      if (!retryable) discardStoredIntent(sessionStorage);
      setProgress("idle");
      setFormError({
        message: error instanceof ApiError ? error.message : retryable ? "Se perdió la conexión. Puedes continuar sin duplicar la operación." : "No se pudo completar la operación.",
        correlationId: error instanceof ApiError ? error.correlationId : null,
        retryable,
      });
      requestAnimationFrame(() => errorRef.current?.focus());
    } finally {
      submissionGuard.current.release();
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!submissionGuard.current.acquire()) return;
    const error = validateMessage(message);
    if (error) {
      submissionGuard.current.release();
      setValidationError(error);
      textareaRef.current?.focus();
      return;
    }
    const payload = payloadFor(message, isDemo);
    let intent = intentRef.current;
    if (!intent || !samePayload(intent.payload, payload)) intent = createIntent(payload);
    persist(intent);
    setFormError(null);
    setRecovered(false);
    void execute(intent);
  }

  const busy = progress !== "idle";
  const describedBy = validationError ? "message-help message-error" : "message-help";
  const progressLabel = progress === "creating_inquiry" ? "Creando consulta…" : progress === "creating_run" ? "Iniciando agente…" : progress === "navigating" ? "Abriendo ejecución…" : null;

  return (
    <form className="inquiry-form" onSubmit={submit} noValidate>
      <div className="demo-note"><span aria-hidden="true">ⓘ</span><p><strong>Datos de demostración.</strong> Esta consulta no ejecuta acciones externas.</p></div>
      {recovered ? <div className="recovery-note" role="status">Encontramos una operación pendiente. Continúa para recuperarla con las mismas claves, sin duplicarla.</div> : null}
      <div className="field">
        <div className="label-row"><label htmlFor="raw-message">Mensaje de la consulta</label><span>{message.length.toLocaleString("es-ES")} / {MESSAGE_MAX_LENGTH.toLocaleString("es-ES")}</span></div>
        <p id="message-help" className="field-help">Describe producto, cantidad, mercado y cualquier requisito comercial disponible.</p>
        <textarea ref={textareaRef} id="raw-message" name="raw-message" rows={10} value={message} aria-invalid={Boolean(validationError)} aria-describedby={describedBy} onChange={(event) => editMessage(event.target.value)} disabled={busy} />
        {validationError ? <p id="message-error" className="field-error">{validationError}</p> : null}
        <button className="text-button" type="button" onClick={loadDemo} disabled={busy}>Cargar escenario UC-001</button>
        {isDemo ? <p className="demo-selection">Escenario UC-001 cargado para Rhein Selection GmbH. Si editas el texto, pasará a ser una consulta manual.</p> : null}
      </div>
      {formError ? (
        <div className="state-card error-card" role="alert" tabIndex={-1} ref={errorRef}>
          <h2>No se pudo completar el envío</h2><p>{formError.message}</p>
          {formError.correlationId ? <p className="correlation">Referencia: {formError.correlationId}</p> : null}
          {formError.retryable ? <p>Pulsa de nuevo para continuar la etapa pendiente con la misma intención.</p> : <button className="text-button" type="button" onClick={() => { discardIntent(); setFormError(null); textareaRef.current?.focus(); }}>Corregir o iniciar una nueva intención</button>}
        </div>
      ) : null}
      <div className="form-actions">
        {busy ? <span className="button button-quiet" aria-disabled="true">Operación en curso</span> : <Link className="button button-quiet" href="/" onClick={discardIntent}>Cancelar y volver</Link>}
        <button className="button button-primary" type="submit" disabled={busy || Boolean(formError && !formError.retryable)} aria-disabled={busy || Boolean(formError && !formError.retryable)}>{progressLabel ?? (formError?.retryable ? "Continuar operación" : formError ? "Corrige la consulta para continuar" : "Crear consulta y ejecutar agente")}</button>
      </div>
      <div className="sr-only" role="status" aria-live="polite">{progressLabel}</div>
    </form>
  );
}
