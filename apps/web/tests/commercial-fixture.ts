import type { RunResult } from "@/lib/api/types";

export const RUN_ID = "22222222-2222-4222-8222-222222222222";
export const INQUIRY_ID = "33333333-3333-4333-8333-333333333333";
export const PRODUCT_ID = "44444444-4444-4444-8444-444444444444";
export const QUOTE_ID = "55555555-5555-4555-8555-555555555555";
export const PROPOSAL_ID = "66666666-6666-4666-8666-666666666666";
export const EMAIL_ID = "77777777-7777-4777-8777-777777777777";
export const CUSTOMER_ID = "88888888-8888-4888-8888-888888888888";
export const OPPORTUNITY_ID = "99999999-9999-4999-8999-999999999999";
export const assumptions = { schema_version:"1.0", unit_price_source:"validated_recommendation_snapshot", taxes_included:false, transport_included:false, insurance_included:false, duties_and_customs_included:false, stock_reserved:false, human_review_required:true };
const line = { product_id:PRODUCT_ID, sku:"ADE-001", name:"Albariño Demo", quantity_bottles:12, cases:2, unit_price_cents:1, line_total_cents:999 };
const snapshot = { quote_id:QUOTE_ID, currency:"EUR", subtotal_cents:999, status:"draft", lines:[line], assumptions };
const buyer = { company_name:"Bodega <script>alert(1)</script>", contact_name:"Ana", email:"ana@example.test", market:"DO", country_code:"DO" };
export function completeResult(overrides: Partial<RunResult> = {}): RunResult {
  return {
    agent_run_id:RUN_ID, status:"completed",
    inquiry:{ id:INQUIRY_ID, customer_id:CUSTOMER_ID, source:"demo", status:"processed", detected_language:"es", received_at:"2026-08-05T12:00:00Z", raw_message:"Hola\n<script>alert(1)</script>", extracted_data:{}, missing_fields:["budget","future_code"], agent_runs:[] },
    analysis:{ schema_version:"1.0", language:"es", intent:"b2b_purchase_inquiry", market:"DO", product_interest:["Albariño"], estimated_bottles:0, channel:null, target_horizon_days:0, target_date:"2026-09-01", samples_requested:false, price_list_requested:true, budget_total_cents:0, budget_currency:"EUR", sample_delivery_address:null, delivery_terms:null, certification_requirements:[], tax_identifier:null, company_name:null, contact_name:null, contact_email:null },
    recommendation:{ schema_version:"1.0", items:[{ product_id:PRODUCT_ID, sku:"ADE-001", name:"Albariño Demo", quantity_bottles:12, units_per_case:6, cases:2, unit_price_cents:0, sellable_bottles:0, certifications:[], rationale:"Selección <b>IA</b>" }], total_bottles:12, currency:"EUR", summary:"Resumen IA", warnings:["Warning local"] , validation_status:"valid" },
    quote:{ id:QUOTE_ID, currency:"EUR", subtotal_cents:999, status:"draft", assumptions, items:[line] },
    artifacts:[
      { id:PROPOSAL_ID, artifact_type:"proposal", language:"es", schema_version:"1.0", review_status:"needs_review", created_at:"2026-08-05T12:05:00Z", content:{ schema_version:"1.0", artifact_type:"proposal", language:"es", buyer, quote:snapshot, narrative:{ schema_version:"1.0", headline:"Propuesta <img>", executive_summary:"Resumen", product_positioning:[{product_id:PRODUCT_ID,positioning:"Posición"}], next_steps:["Revisar"], open_questions:["¿Confirmar?"], warnings:["Warning proposal"] }, review_status:"needs_review" } },
      { id:EMAIL_ID, artifact_type:"email_draft", language:"es", schema_version:"1.0", review_status:"needs_review", created_at:"2026-08-05T12:06:00Z", content:{ schema_version:"1.0", artifact_type:"email_draft", language:"es", recipient:buyer, proposal_artifact_id:PROPOSAL_ID, commercial_block:snapshot, narrative:{ schema_version:"1.0", subject:"Asunto", introduction:"Hola", recommendation_summary:"Resumen", next_step:"Responder", questions:["¿Cantidad?"], closing:"Saludos", warnings:["Warning email"] }, review_status:"needs_review" } },
    ],
    customer:{id:CUSTOMER_ID,company_name:"Bodega Demo",country_code:"DO",preferred_language:"es"},
    opportunity:{id:OPPORTUNITY_ID,inquiry_id:INQUIRY_ID,customer_id:CUSTOMER_ID,title:"Venta demo",stage:"proposal_draft",priority:"high",score:0,market:"DO",channel:null,estimated_bottles:0,target_date:null,summary:"Interno",created_at:"2026-08-05T12:07:00Z",updated_at:"2026-08-05T12:07:00Z"},
    followup:{id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",opportunity_id:OPPORTUNITY_ID,title:"Revisar",due_at:"2026-08-06T12:00:00Z",status:"pending",created_at:"2026-08-05T12:08:00Z"},
    memory_summary:[
      {id:"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",customer_id:CUSTOMER_ID,category:"preference",content:"Actual",confidence:0,source_inquiry_id:INQUIRY_ID,created_at:"2026-08-05T12:00:00Z"},
      {id:"cccccccc-cccc-4ccc-8ccc-cccccccccccc",customer_id:CUSTOMER_ID,category:"history",content:"Anterior",confidence:0.8,source_inquiry_id:"dddddddd-dddd-4ddd-8ddd-dddddddddddd",created_at:"2026-08-04T12:00:00Z"},
      {id:"eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",customer_id:CUSTOMER_ID,category:"unknown",content:"Sin fuente",confidence:1,source_inquiry_id:null,created_at:"2026-08-03T12:00:00Z"},
    ], warnings:["Warning global"], ...overrides,
  };
}
