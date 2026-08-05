import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));

import { InquiryForm } from "@/components/inquiry-form";
import { RecentRunsView } from "@/components/recent-runs";
import HomePage from "@/app/page";
import RunPage from "@/app/runs/[runId]/page";

const run = {
  id: "22222222-2222-4222-8222-222222222222", inquiry_id: "11111111-1111-4111-8111-111111111111",
  retry_of_run_id: null, status: "queued" as const, current_step: "queued", company_name: null,
  market: null, received_at: "2026-08-04T12:30:00Z", started_at: "2026-08-04T12:30:00Z",
  completed_at: null, error_code: null, retryable: false,
};

describe("Block 2 component states and routes", () => {
  it("keeps the new inquiry CTA alongside the announced loading state", () => {
    const html = renderToStaticMarkup(<HomePage />);
    expect(html).toContain('href="/inquiries/new"');
    expect(html).toContain("Nueva consulta");
    expect(html).toContain('role="status"');
    expect(html).toContain("Cargando ejecuciones recientes");
  });

  it("renders empty, error with correlation and retry, and ordered run links", () => {
    const empty = renderToStaticMarkup(<RecentRunsView state={{ kind: "ready", runs: [] }} onRetry={vi.fn()} />);
    expect(empty).toContain("Crear primera consulta");
    const error = renderToStaticMarkup(<RecentRunsView state={{ kind: "error", message: "Safe message", correlationId: "corr-1" }} onRetry={vi.fn()} />);
    expect(error).toContain("Safe message");
    expect(error).toContain("corr-1");
    expect(error).toContain("Volver a intentar");
    const list = renderToStaticMarkup(<RecentRunsView state={{ kind: "ready", runs: [run, { ...run, id: "33333333-3333-4333-8333-333333333333", company_name: "Second" }] }} onRetry={vi.fn()} />);
    expect(list.indexOf(run.id)).toBeLessThan(list.indexOf("33333333-3333-4333-8333-333333333333"));
    expect(list).toContain("Empresa no disponible");
    expect(list).toContain("Mercado no disponible");
    expect(list).toContain(`href="/runs/${run.id}"`);
    expect(list).toContain("Abrir ejecución de Empresa no disponible");
  });

  it("renders the labelled, described form and announced progress region", () => {
    const html = renderToStaticMarkup(<InquiryForm />);
    expect(html).toContain('for="raw-message"');
    expect(html).toContain('aria-describedby="message-help"');
    expect(html).toContain("10.000");
    expect(html).toContain("Cargar escenario UC-001");
    expect(html).toContain("Crear consulta y ejecutar agente");
    expect(html).toContain('aria-live="polite"');
  });

  it("renders the observable workspace for a UUID and rejects malformed IDs locally", async () => {
    const page = await RunPage({ params: Promise.resolve({ runId: run.id }) });
    const html = renderToStaticMarkup(page);
    expect(html).toContain("Cargando ejecución");
    const invalidPage = await RunPage({ params: Promise.resolve({ runId: "not-a-run" }) });
    const invalidHtml = renderToStaticMarkup(invalidPage);
    expect(invalidHtml).toContain("Identificador no válido");
    expect(invalidHtml).toContain("No se realizó ninguna consulta");
  });
});
