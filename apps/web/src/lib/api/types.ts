export type UUID = string;
export type JsonObject = Record<string, unknown>;
export type AgentRunStatus = "queued" | "running" | "needs_review" | "completed" | "failed";
export type AgentRunStep = string;
export type InquiryStatus = string;

export interface HealthResponse { status: "ok"; service: string; version: string; environment: string; qwen_configured: boolean; }
export interface ErrorBody { code: string; message: string; details: JsonObject; correlation_id: UUID; }
export interface ErrorEnvelope { error: ErrorBody; }
export interface InquiryCreate { source: "manual" | "demo"; raw_message: string; customer_id?: UUID | null; }
export interface InquirySummary { id: UUID; customer_id: UUID | null; source: string; status: InquiryStatus; detected_language: string | null; received_at: string; }
export interface InquiryList { items: InquirySummary[]; limit: number; offset: number; }
export interface RunReference { id: UUID; status: AgentRunStatus; current_step: AgentRunStep; started_at: string; completed_at: string | null; }
export interface InquiryDetail extends InquirySummary { raw_message: string; extracted_data: JsonObject; missing_fields: string[]; agent_runs: RunReference[]; }
export interface RunAccepted { agent_run_id: UUID; inquiry_id: UUID; status: AgentRunStatus; current_step: AgentRunStep; correlation_id: UUID; retry_of_run_id: UUID | null; poll_url: string; }
export interface PublicRunError { code: string; message: string; }
export interface RunReferences { quote_id: UUID | null; proposal_id: UUID | null; email_draft_id: UUID | null; opportunity_id: UUID | null; followup_task_id: UUID | null; }
export interface AgentRunDetail { id: UUID; inquiry_id: UUID; retry_of_run_id: UUID | null; correlation_id: UUID; status: AgentRunStatus; current_step: AgentRunStep; started_at: string; completed_at: string | null; model: string; prompt_versions: JsonObject; error: PublicRunError | null; retryable: boolean; references: RunReferences; last_event_sequence: number; events_url: string; result_url: string; }
export interface AgentRunSummary { id: UUID; inquiry_id: UUID; retry_of_run_id: UUID | null; status: AgentRunStatus; current_step: AgentRunStep; company_name: string | null; market: string | null; received_at: string; started_at: string; completed_at: string | null; error_code: string | null; retryable: boolean; }
export interface AgentRunList { items: AgentRunSummary[]; limit: number; offset: number; }
export interface PublicEvent { sequence: number; event_type: string; step: AgentRunStep; payload: JsonObject & { tool_name?: string }; created_at: string; }
export interface EventList { agent_run_id: UUID; events: PublicEvent[]; last_sequence: number; terminal: boolean; }
export interface QuoteItemPublic { product_id: UUID; sku: string; name: string; quantity_bottles: number; unit_price_cents: number; line_total_cents: number; cases: number; }
export interface QuotePublic { id: UUID; currency: "EUR"; subtotal_cents: number; status: string; assumptions: JsonObject; items: QuoteItemPublic[]; }
export interface ArtifactPublic { id: UUID; artifact_type: string; language: string; schema_version: string; content: JsonObject; review_status: string; created_at: string; }
export interface CustomerPublic { id: UUID; company_name: string; country_code: string; preferred_language: string; }
export interface OpportunityPublic { id: UUID; inquiry_id: UUID; customer_id: UUID; title: string; stage: string; priority: string; score: number; market: string; channel: string | null; estimated_bottles: number | null; target_date: string | null; summary: string; created_at: string; updated_at: string; }
export interface FollowUpPublic { id: UUID; opportunity_id: UUID; title: string; due_at: string; status: string; created_at: string; }
export interface MemoryPublic { id: UUID; customer_id: UUID; category: string; content: string; confidence: number; source_inquiry_id: UUID | null; created_at: string; }
export interface MemoryList { customer_id: UUID; items: MemoryPublic[]; limit: number; offset: number; }
export interface RunResult { agent_run_id: UUID; status: AgentRunStatus; inquiry: InquiryDetail; analysis: JsonObject | null; recommendation: JsonObject | null; quote: QuotePublic | null; artifacts: ArtifactPublic[]; customer: CustomerPublic | null; opportunity: OpportunityPublic | null; followup: FollowUpPublic | null; memory_summary: MemoryPublic[]; warnings: string[]; }
export interface OpportunityDetail extends OpportunityPublic { customer: CustomerPublic; quote: QuotePublic | null; artifacts: ArtifactPublic[]; followup: FollowUpPublic | null; }
