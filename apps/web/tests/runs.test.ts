import { describe, expect, it } from "vitest";

import { formatReceivedAt, presentRun, runStatusLabel } from "@/lib/runs";

describe("run presentation", () => {
  it("uses text status labels and null fallbacks", () => {
    expect(runStatusLabel("needs_review")).toBe("Listo para revisión");
    expect(presentRun({ id:"r", inquiry_id:"i", retry_of_run_id:null, status:"queued", current_step:"queued", company_name:null, market:null, received_at:"invalid", started_at:"", completed_at:null, error_code:null, retryable:false })).toMatchObject({ company:"Empresa no disponible", market:"Mercado no disponible", receivedAt:"Fecha no disponible", status:"En cola" });
  });
  it("formats valid dates for the interface locale", () => {
    expect(formatReceivedAt("2026-08-04T12:30:00Z", "es-ES")).toContain("2026");
  });
});
