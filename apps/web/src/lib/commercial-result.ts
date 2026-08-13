import type { AgentRunStatus, RunResult, UUID } from "@/lib/api/types";

export type Section<T> =
  | { state: "available"; value: T }
  | { state: "empty" | "missing" | "incompatible" };

export type AssumptionsVm = {
  unitPriceSource: "validated_recommendation_snapshot";
  taxesIncluded: false;
  transportIncluded: false;
  insuranceIncluded: false;
  dutiesAndCustomsIncluded: false;
  stockReserved: false;
  humanReviewRequired: true;
};
export type QuoteLineVm = { productId: UUID; sku: string; name: string; quantityBottles: number; cases: number; unitPriceCents: number; lineTotalCents: number };
export type QuoteVm = { id: UUID; currency: "EUR"; subtotalCents: number; status: string; assumptions: Section<AssumptionsVm>; items: QuoteLineVm[] };
export type AnalysisVm = Record<string, string | number | boolean | string[] | null> & { schema_version: "1.0" };
export type RecommendationVm = { summary: string; totalBottles: number; currency: "EUR"; warnings: string[]; items: Array<{ productId: UUID; sku: string; name: string; quantityBottles: number; unitsPerCase: number; cases: number; unitPriceCents: number; sellableBottles: number; certifications: string[]; rationale: string }> };
type BuyerVm = { companyName: string | null; contactName: string | null; email: string | null; market: string | null; countryCode: string | null };
export type ProposalVm = { id: UUID; language: string; createdAt: string; buyer: BuyerVm; quote: QuoteVm; headline: string; executiveSummary: string; positioning: Array<{ productId: UUID; text: string }>; nextSteps: string[]; openQuestions: string[]; warnings: string[] };
export type EmailVm = { id: UUID; language: string; createdAt: string; recipient: BuyerVm; proposalId: UUID; quote: QuoteVm; subject: string; introduction: string; recommendationSummary: string; questions: string[]; nextStep: string; closing: string; warnings: string[] };
export type ArtifactVm = { kind: "proposal"; value: ProposalVm } | { kind: "email"; value: EmailVm } | { kind: "incompatible"; id: UUID; artifactType: string };

export type CommercialResultVm = {
  agentRunId: UUID; status: "completed" | "needs_review" | "failed";
  inquiry: RunResult["inquiry"];
  analysis: Section<AnalysisVm>; recommendation: Section<RecommendationVm>; quote: Section<QuoteVm>;
  artifacts: ArtifactVm[]; customer: RunResult["customer"]; opportunity: RunResult["opportunity"];
  followup: RunResult["followup"]; memory: RunResult["memory_summary"]; warnings: string[];
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const terminal = new Set<AgentRunStatus>(["completed", "needs_review", "failed"]);
const object = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === "object" && !Array.isArray(value));
const exact = (value: Record<string, unknown>, keys: readonly string[]) => Object.keys(value).every((key) => keys.includes(key)) && keys.every((key) => key in value);
const string = (value: unknown): value is string => typeof value === "string";
const nullableString = (value: unknown): value is string | null => value === null || string(value);
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const integer = (value: unknown): value is number => finite(value) && Number.isInteger(value);
const bool = (value: unknown): value is boolean => typeof value === "boolean";
const uuid = (value: unknown): value is UUID => string(value) && UUID_RE.test(value);
const dateString = (value: unknown): value is string => string(value) && !Number.isNaN(Date.parse(value));
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(string);

function buyer(value: unknown): BuyerVm | null {
  if (!object(value) || !exact(value, ["company_name", "contact_name", "email", "market", "country_code"])) return null;
  if (![value.company_name, value.contact_name, value.email, value.market, value.country_code].every(nullableString)) return null;
  return { companyName: value.company_name as string | null, contactName: value.contact_name as string | null, email: value.email as string | null, market: value.market as string | null, countryCode: value.country_code as string | null };
}

export function guardAssumptions(value: unknown): AssumptionsVm | null {
  const keys = ["schema_version", "unit_price_source", "taxes_included", "transport_included", "insurance_included", "duties_and_customs_included", "stock_reserved", "human_review_required"] as const;
  if (!object(value) || !exact(value, keys) || value.schema_version !== "1.0" || value.unit_price_source !== "validated_recommendation_snapshot" || value.taxes_included !== false || value.transport_included !== false || value.insurance_included !== false || value.duties_and_customs_included !== false || value.stock_reserved !== false || value.human_review_required !== true) return null;
  return { unitPriceSource: value.unit_price_source, taxesIncluded: false, transportIncluded: false, insuranceIncluded: false, dutiesAndCustomsIncluded: false, stockReserved: false, humanReviewRequired: true };
}

function quoteLine(value: unknown, artifact = false): QuoteLineVm | null {
  const keys = artifact ? ["product_id", "sku", "name", "quantity_bottles", "cases", "unit_price_cents", "line_total_cents"] : ["product_id", "sku", "name", "quantity_bottles", "unit_price_cents", "line_total_cents", "cases"];
  if (!object(value) || !exact(value, keys) || !uuid(value.product_id) || !string(value.sku) || !string(value.name) || !integer(value.quantity_bottles) || !integer(value.cases) || !integer(value.unit_price_cents) || !integer(value.line_total_cents)) return null;
  return { productId: value.product_id, sku: value.sku, name: value.name, quantityBottles: value.quantity_bottles, cases: value.cases, unitPriceCents: value.unit_price_cents, lineTotalCents: value.line_total_cents };
}

function quoteSnapshot(value: unknown): QuoteVm | null {
  if (!object(value) || !exact(value, ["quote_id", "currency", "subtotal_cents", "status", "lines", "assumptions"]) || !uuid(value.quote_id) || value.currency !== "EUR" || !integer(value.subtotal_cents) || !string(value.status) || !Array.isArray(value.lines)) return null;
  const items = value.lines.map((line) => quoteLine(line, true));
  if (items.some((line) => line === null)) return null;
  const assumptions = guardAssumptions(value.assumptions);
  return { id: value.quote_id, currency: "EUR", subtotalCents: value.subtotal_cents, status: value.status, items: items as QuoteLineVm[], assumptions: assumptions ? { state: "available", value: assumptions } : { state: "incompatible" } };
}

export function guardAnalysis(value: unknown): AnalysisVm | null {
  const keys = ["schema_version", "language", "intent", "market", "product_interest", "estimated_bottles", "channel", "target_horizon_days", "target_date", "samples_requested", "price_list_requested", "budget_total_cents", "budget_currency", "sample_delivery_address", "delivery_terms", "certification_requirements", "tax_identifier", "company_name", "contact_name", "contact_email"] as const;
  if (!object(value) || !exact(value, keys) || value.schema_version !== "1.0" || !string(value.language) || !string(value.intent) || !nullableString(value.market) || !strings(value.product_interest) || !(value.estimated_bottles === null || integer(value.estimated_bottles)) || !nullableString(value.channel) || !(value.target_horizon_days === null || integer(value.target_horizon_days)) || !(value.target_date === null || dateString(value.target_date)) || !bool(value.samples_requested) || !bool(value.price_list_requested) || !(value.budget_total_cents === null || integer(value.budget_total_cents)) || !nullableString(value.budget_currency) || !nullableString(value.sample_delivery_address) || !nullableString(value.delivery_terms) || !strings(value.certification_requirements) || !nullableString(value.tax_identifier) || !nullableString(value.company_name) || !nullableString(value.contact_name) || !nullableString(value.contact_email)) return null;
  return value as AnalysisVm;
}

export function guardRecommendation(value: unknown): RecommendationVm | null {
  if (!object(value) || !exact(value, ["schema_version", "items", "total_bottles", "currency", "summary", "warnings", "validation_status"]) || value.schema_version !== "1.0" || value.currency !== "EUR" || value.validation_status !== "valid" || !integer(value.total_bottles) || !string(value.summary) || !strings(value.warnings) || !Array.isArray(value.items) || value.items.length === 0) return null;
  const items = value.items.map((item) => {
    const keys = ["product_id", "sku", "name", "quantity_bottles", "units_per_case", "cases", "unit_price_cents", "sellable_bottles", "certifications", "rationale"];
    if (!object(item) || !exact(item, keys) || !uuid(item.product_id) || !string(item.sku) || !string(item.name) || !integer(item.quantity_bottles) || !integer(item.units_per_case) || !integer(item.cases) || !integer(item.unit_price_cents) || !integer(item.sellable_bottles) || !strings(item.certifications) || !string(item.rationale)) return null;
    return { productId: item.product_id, sku: item.sku, name: item.name, quantityBottles: item.quantity_bottles, unitsPerCase: item.units_per_case, cases: item.cases, unitPriceCents: item.unit_price_cents, sellableBottles: item.sellable_bottles, certifications: item.certifications, rationale: item.rationale };
  });
  return items.some((item) => item === null) ? null : { summary: value.summary, totalBottles: value.total_bottles, currency: "EUR", warnings: value.warnings, items: items as RecommendationVm["items"] };
}

function publicQuote(value: unknown): QuoteVm | null {
  if (!object(value) || !exact(value, ["id", "currency", "subtotal_cents", "status", "assumptions", "items"]) || !uuid(value.id) || value.currency !== "EUR" || !integer(value.subtotal_cents) || !string(value.status) || !Array.isArray(value.items)) return null;
  const items = value.items.map((item) => quoteLine(item));
  if (items.some((item) => item === null)) return null;
  const assumptions = guardAssumptions(value.assumptions);
  return { id: value.id, currency: "EUR", subtotalCents: value.subtotal_cents, status: value.status, items: items as QuoteLineVm[], assumptions: assumptions ? { state: "available", value: assumptions } : { state: "incompatible" } };
}

function artifact(value: unknown): ArtifactVm | null {
  if (!object(value) || !exact(value, ["id", "artifact_type", "language", "schema_version", "content", "review_status", "created_at"]) || !uuid(value.id) || !string(value.artifact_type) || !string(value.language) || !string(value.schema_version) || !object(value.content) || !string(value.review_status) || !dateString(value.created_at)) return null;
  const incompatible = (): ArtifactVm => ({ kind: "incompatible", id: value.id as UUID, artifactType: value.artifact_type as string });
  if (value.schema_version !== "1.0" || value.review_status !== "needs_review") return incompatible();
  const content = value.content;
  if (value.artifact_type === "proposal") {
    if (!exact(content, ["schema_version", "artifact_type", "language", "buyer", "quote", "narrative", "review_status"]) || content.schema_version !== "1.0" || content.artifact_type !== "proposal" || content.language !== value.language || content.review_status !== value.review_status) return incompatible();
    const b = buyer(content.buyer), q = quoteSnapshot(content.quote), n = content.narrative;
    if (!b || !q || !object(n) || !exact(n, ["schema_version", "headline", "executive_summary", "product_positioning", "next_steps", "open_questions", "warnings"]) || n.schema_version !== "1.0" || !string(n.headline) || !string(n.executive_summary) || !Array.isArray(n.product_positioning) || !strings(n.next_steps) || !strings(n.open_questions) || !strings(n.warnings)) return incompatible();
    const positioning = n.product_positioning.map((item) => object(item) && exact(item, ["product_id", "positioning"]) && uuid(item.product_id) && string(item.positioning) ? { productId: item.product_id, text: item.positioning } : null);
    if (positioning.some((item) => item === null)) return incompatible();
    return { kind: "proposal", value: { id: value.id, language: value.language, createdAt: value.created_at, buyer: b, quote: q, headline: n.headline, executiveSummary: n.executive_summary, positioning: positioning as ProposalVm["positioning"], nextSteps: n.next_steps, openQuestions: n.open_questions, warnings: n.warnings } };
  }
  if (value.artifact_type === "email_draft") {
    if (!exact(content, ["schema_version", "artifact_type", "language", "recipient", "proposal_artifact_id", "commercial_block", "narrative", "review_status"]) || content.schema_version !== "1.0" || content.artifact_type !== "email_draft" || content.language !== value.language || content.review_status !== value.review_status || !uuid(content.proposal_artifact_id)) return incompatible();
    const b = buyer(content.recipient), q = quoteSnapshot(content.commercial_block), n = content.narrative;
    if (!b || !q || !object(n) || !exact(n, ["schema_version", "subject", "introduction", "recommendation_summary", "next_step", "questions", "closing", "warnings"]) || n.schema_version !== "1.0" || !string(n.subject) || !string(n.introduction) || !string(n.recommendation_summary) || !string(n.next_step) || !strings(n.questions) || !string(n.closing) || !strings(n.warnings)) return incompatible();
    return { kind: "email", value: { id: value.id, language: value.language, createdAt: value.created_at, recipient: b, proposalId: content.proposal_artifact_id, quote: q, subject: n.subject, introduction: n.introduction, recommendationSummary: n.recommendation_summary, questions: n.questions, nextStep: n.next_step, closing: n.closing, warnings: n.warnings } };
  }
  return incompatible();
}

const runReference = (v: unknown) => object(v) && exact(v,["id","status","current_step","started_at","completed_at"]) && uuid(v.id) && string(v.status) && string(v.current_step) && dateString(v.started_at) && (v.completed_at===null || dateString(v.completed_at));
const validInquiry = (v: unknown): v is RunResult["inquiry"] => object(v) && exact(v,["id","customer_id","source","status","detected_language","received_at","raw_message","extracted_data","missing_fields","agent_runs"]) && uuid(v.id) && (v.customer_id === null || uuid(v.customer_id)) && string(v.source) && string(v.status) && (v.detected_language === null || string(v.detected_language)) && dateString(v.received_at) && string(v.raw_message) && object(v.extracted_data) && strings(v.missing_fields) && Array.isArray(v.agent_runs) && v.agent_runs.every(runReference);
const validCustomer = (v: unknown): v is NonNullable<RunResult["customer"]> => object(v) && exact(v,["id","company_name","country_code","preferred_language"]) && uuid(v.id) && string(v.company_name) && string(v.country_code) && string(v.preferred_language);
const validOpportunity = (v: unknown): v is NonNullable<RunResult["opportunity"]> => object(v) && exact(v,["id","inquiry_id","customer_id","title","stage","priority","score","market","channel","estimated_bottles","target_date","summary","created_at","updated_at"]) && uuid(v.id) && uuid(v.inquiry_id) && uuid(v.customer_id) && string(v.title) && string(v.stage) && string(v.priority) && integer(v.score) && string(v.market) && nullableString(v.channel) && (v.estimated_bottles === null || integer(v.estimated_bottles)) && (v.target_date === null || dateString(v.target_date)) && string(v.summary) && dateString(v.created_at) && dateString(v.updated_at);
const validFollowup = (v: unknown): v is NonNullable<RunResult["followup"]> => object(v) && exact(v,["id","opportunity_id","title","due_at","status","created_at"]) && uuid(v.id) && uuid(v.opportunity_id) && string(v.title) && dateString(v.due_at) && string(v.status) && dateString(v.created_at);
const validMemory = (v: unknown): v is RunResult["memory_summary"][number] => object(v) && exact(v,["id","customer_id","category","content","confidence","source_inquiry_id","created_at"]) && uuid(v.id) && uuid(v.customer_id) && string(v.category) && string(v.content) && finite(v.confidence) && (v.source_inquiry_id === null || uuid(v.source_inquiry_id)) && dateString(v.created_at);

export class ResultContractError extends Error {}
export function adaptRunResult(payload: unknown, expectedRunId: UUID, expectedStatus: AgentRunStatus): CommercialResultVm {
  if (!object(payload) || !exact(payload, ["agent_run_id", "status", "inquiry", "analysis", "recommendation", "quote", "artifacts", "customer", "opportunity", "followup", "memory_summary", "warnings"]) || !uuid(payload.agent_run_id) || !terminal.has(payload.status as AgentRunStatus) || payload.agent_run_id !== expectedRunId || payload.status !== expectedStatus || !validInquiry(payload.inquiry) || !Array.isArray(payload.artifacts) || !(payload.customer === null || validCustomer(payload.customer)) || !(payload.opportunity === null || validOpportunity(payload.opportunity)) || !(payload.followup === null || validFollowup(payload.followup)) || !Array.isArray(payload.memory_summary) || !payload.memory_summary.every(validMemory) || !strings(payload.warnings)) throw new ResultContractError("RunResult incompatible");
  const analysis = payload.analysis === null ? { state: "missing" as const } : guardAnalysis(payload.analysis) ? { state: "available" as const, value: guardAnalysis(payload.analysis)! } : { state: "incompatible" as const };
  const recommendation = payload.recommendation === null ? { state: "missing" as const } : guardRecommendation(payload.recommendation) ? { state: "available" as const, value: guardRecommendation(payload.recommendation)! } : { state: "incompatible" as const };
  const quote = payload.quote === null ? { state: "missing" as const } : publicQuote(payload.quote) ? { state: "available" as const, value: publicQuote(payload.quote)! } : { state: "incompatible" as const };
  const artifacts = payload.artifacts.map(artifact);
  if (artifacts.some((item) => item === null)) throw new ResultContractError("ArtifactPublic incompatible");
  return { agentRunId: payload.agent_run_id, status: payload.status as CommercialResultVm["status"], inquiry: payload.inquiry, analysis, recommendation, quote, artifacts: artifacts as ArtifactVm[], customer: payload.customer, opportunity: payload.opportunity, followup: payload.followup, memory: payload.memory_summary, warnings: payload.warnings };
}

export function formatEuro(cents: number): string { return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", minimumFractionDigits: 2 }).format(cents / 100); }
export function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.valueOf()) ? "Fecha no válida" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: value.includes("T") ? "short" : undefined }).format(date); }
export function missingFieldLabel(code: string): string { return ({ market: "Mercado", product_interest: "Productos de interés", estimated_bottles: "Volumen estimado", channel: "Canal", target_date: "Fecha objetivo", budget: "Presupuesto", delivery_terms: "Condiciones de entrega", certification_requirements: "Certificaciones", tax_identifier: "Identificación fiscal", sample_delivery_address: "Dirección para muestras" } as Record<string, string>)[code] ?? `Dato pendiente no reconocido (${code})`; }
export function memorySourceLabel(source: UUID | null, inquiry: UUID): string { return source === null ? "Procedencia no disponible" : source === inquiry ? "Consulta actual" : "Interacción anterior"; }
const assumptionsText = ["Precio procedente de la recomendación validada", "Impuestos no incluidos", "Transporte no incluido", "Seguro no incluido", "Aranceles y aduanas no incluidos", "Stock no reservado", "Revisión humana requerida"];
export function assumptionLabels(): string[] { return [...assumptionsText]; }
function quoteText(q: QuoteVm): string[] { return ["CÁLCULO DETERMINISTA", ...q.items.map((i) => `${i.name} (${i.sku}): ${i.quantityBottles} botellas, ${i.cases} cajas, ${formatEuro(i.unitPriceCents)} por botella, ${formatEuro(i.lineTotalCents)}`), `Subtotal: ${formatEuro(q.subtotalCents)}`]; }
export function proposalClipboard(p: ProposalVm): string { return ["BORRADOR — REQUIERE REVISIÓN HUMANA", "TEXTO GENERADO POR IA — BORRADOR", p.headline, p.executiveSummary, ...p.positioning.map((x) => `${x.productId}: ${x.text}`), ...p.nextSteps, ...p.openQuestions, ...p.warnings, ...quoteText(p.quote)].join("\n"); }
export function emailClipboard(e: EmailVm): string { return ["BORRADOR — NO ENVIADO", "TEXTO GENERADO POR IA — BORRADOR", e.introduction, e.recommendationSummary, ...e.questions, e.nextStep, e.closing, ...e.warnings, ...quoteText(e.quote)].join("\n"); }
export async function writePlainText(text: string, clipboard: Pick<Clipboard, "writeText"> | undefined): Promise<"Copiado" | "No se pudo copiar"> {
  if (!clipboard) return "No se pudo copiar";
  try { await clipboard.writeText(text); return "Copiado"; } catch { return "No se pudo copiar"; }
}
