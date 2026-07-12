# Structured inquiry analysis — Sprint 2 Block 4

## Objective

Convert one persisted commercial inquiry into validated structured data, compute clarification needs deterministically and persist the result without starting the orchestrator or frontend.

## Implemented capability

The block adds:

- versioned prompt `inquiry_analysis.v1`;
- Pydantic schema `InquiryAnalysis`;
- normalized language, market and currency codes;
- bounded commercial intent classification;
- deterministic missing-field calculation;
- repository operations for inquiry status and analysis persistence;
- `InquiryAnalysisService` behind a provider-neutral JSON completion protocol;
- safe failure states for invalid model output and provider errors;
- unit and integration tests.

## Processing sequence

```text
load inquiry
  -> mark processing and commit
  -> call Qwen JSON mode outside a database transaction
  -> validate with Pydantic
  -> compute missing fields in application code
  -> persist extraction and completed status
```

A provider call is never made while a SQLite write transaction remains open.

## Persisted fields

The service updates only existing `inquiries` columns:

- `detected_language`;
- `status`;
- `extracted_data`;
- `missing_fields`.

No migration is required for this block.

## Structured schema

The schema includes:

- schema version;
- message language;
- commercial intent;
- destination market;
- product interests;
- estimated bottle volume;
- channel;
- relative horizon and exact target date;
- sample and price-list requests;
- budget and currency;
- sample delivery address;
- delivery terms;
- certification requirements;
- tax identifier;
- optional company and contact information.

Unknown nullable values remain `null`. Unknown lists remain empty. Extra properties are rejected.

## Deterministic missing fields

The model does not return `missing_fields`.

For purchase, price and sample intents, application code evaluates:

- market;
- product interest;
- estimated bottles;
- channel;
- exact target date;
- budget;
- delivery terms;
- certification requirements;
- tax identifier;
- sample delivery address when samples are requested.

For product-information inquiries, only market and product interest are required by this phase.

This prevents the model from deciding business completeness inconsistently.

## Error behavior

| Condition | Safe code | Persisted status |
|---|---|---|
| Inquiry not found | `INQUIRY_NOT_FOUND` | unchanged |
| Invalid schema after provider repair | `MODEL_INVALID_JSON` | `failed` |
| Qwen timeout | provider code, such as `QWEN_TIMEOUT` | `failed` |
| Unexpected provider failure | `MODEL_ANALYSIS_FAILED` | `failed` |

Provider exception internals are not persisted or exposed.

## Scope exclusions

This block does not add:

- HTTP inquiry endpoints;
- customer resolution or profile creation;
- customer-memory retrieval;
- catalog or stock selection;
- tool registry;
- recommendation;
- opportunity scoring;
- write tools;
- frontend work.

Those capabilities remain in subsequent Sprint 2 blocks.

## Tests

The block covers:

- primary German B2B inquiry;
- normalization and deduplication;
- exact expected clarification fields;
- product-information minimal requirements;
- invalid structured output;
- provider timeout;
- unknown inquiry;
- packaged prompt loading.

## Next block

Sprint 2 Block 5: bounded orchestration and recommendation using the approved read tools and validated inquiry analysis.
