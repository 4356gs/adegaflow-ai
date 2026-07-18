# Changelog

## Unreleased

### Added

- SQLAlchemy 2.0 persistence boundary and SQLite session management.
- Initial Alembic migration for products, inventory, customers, inquiries, memories and opportunities.
- Reproducible, idempotent demo seed dataset.
- Repository adapters for catalog, stock and customer history.
- Typed tools: `search_catalog`, `get_product_details`, `check_stock` and `retrieve_customer_history`.
- Unit and integration tests for migrations, seeds, stock rules and tool contracts.
- Docker persistent SQLite volume and database commands.
- Versioned `inquiry_analysis.v1` prompt packaged with the API.
- Typed structured inquiry schema and deterministic missing-field rules.
- Inquiry-analysis service with validated persistence and safe failure states.
- Unit and integration tests for normalization, persistence and provider failures.
- Persistent agent runs, tool executions and ordered orchestration events.
- Closed and typed registry for the four approved read-only tools.
- Versioned `product_recommendation.v1` prompt.
- Bounded Qwen tool-calling orchestration with explicit run budgets.
- Deterministic product recommendation enrichment and validation.
- Controlled recommendation correction and safe terminal run states.
- Unit and integration tests for migration, registry, validation and orchestration.
- Reversible quote and generated-artifact migration.
- Deterministic EUR quote calculation using integer cents and verified product snapshots.
- Versioned `proposal_writer.v1` and `email_writer.v1` prompts.
- Strict proposal and email-draft schemas with backend-owned commercial data.
- Persistent proposal and email artifacts requiring human review.
- Partial-result handling that preserves a valid quote when narrative generation fails.
- Unit, migration and orchestration coverage for quote and artifact generation.
- Reversible follow-up and internal-action receipt migration.
- Deterministic customer resolution and CRM opportunity qualification.
- Seven-day follow-up creation through an injected UTC clock.
- Explicit, limited and deduplicated commercial memory persistence.
- Canonical SHA-256 fingerprints and persistent idempotency receipts.
- Atomic orchestration of opportunity, follow-up, memory, audit and terminal state.
- Unit, migration and orchestration coverage for internal actions and rollback.
- ADR-014 for versioned HTTP commands and recoverable local asynchronous execution.
- Binding Sprint 2 Block 8 implementation plan for inquiries, runs, polling,
  results and retry.
- Acceptance scenarios for HTTP idempotency, process interruption, retry and
  route versioning.

### Changed

- Product model now records recommended commercial channels in addition to markets.
- Project status reflects the approved Qwen live spike.
- Project status now records Sprint 2 Block 5 as implemented and verified.
- Project status now records Sprint 2 Block 6 as implemented and verified.
- Successful backend runs now continue through quote and artifact generation and
  terminate in `needs_review`.
- Successful backend runs now continue through atomic internal actions while
  preserving human review as the terminal state.
- API contracts now keep product routes under `/api/v1`, use idempotent POST
  commands and exclude artifact approval from Block 8.

## 0.1.0 — 2026-07-10

### Added

- FastAPI bootstrap and health endpoints.
- Typed environment configuration and JSON logging.
- Qwen Cloud OpenAI-compatible client boundary.
- JSON Object mode validation.
- Function-call normalization.
- Safe provider error taxonomy.
- Qwen integration spike scripts.
- Docker and GitHub Actions configuration.
- Unit tests for bootstrap and adapter behavior.

### Not completed

- Domain model and persistence.
- Commercial tools and orchestrator.
- Web application.
