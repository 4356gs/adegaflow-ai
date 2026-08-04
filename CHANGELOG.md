# Changelog

## Unreleased

### Added

- Sprint 3 Block 1 Next.js web foundation with strict TypeScript, Tailwind CSS,
  accessible demo shell and standalone container build.
- Same-origin `/api/health` and `/api/v1/*` proxy with safe transport errors,
  correlation IDs and restricted header forwarding.
- Centralized manual TypeScript contracts and typed client for every P0 backend
  endpoint.
- Frontend lint, type, unit/contract test, production-build and CI gates.

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
- Reversible `0005_http_async_runs` migration for inquiry submission keys, run
  request keys and immutable retry lineage.
- Strict `/api/v1` inquiry, run, event, result, opportunity and memory contracts
  with uniform safe error envelopes and correlation IDs.
- Bounded one-consumer local dispatcher that processes each run with an
  independent SQLAlchemy session outside the HTTP request.
- Startup recovery that closes interrupted runs and tool executions with
  `RUN_INTERRUPTED` without automatically replaying external calls.
- Closed retry policy that creates a new auditable run and preserves the
  original attempt.
- Contract, migration, dispatcher, recovery, idempotency and OpenAPI tests for
  Sprint 2 Block 8.
- Complete inspectable Qwen provider mock for deterministic backend
  verification without network or provider credentials.
- End-to-end HTTP tests using the real application lifespan, one-consumer
  dispatcher, services, repositories, SQLite and public read models.
- Reproducible `demo-backend` and `demo-backend-retry` terminal runners.
- Sprint 2 Block 9 AT/B9 traceability and verified closure-candidate evidence,
  including Docker build, migration, seed, health and one-worker runtime checks.

### Changed

- Public tool events may expose `payload.tool_name`; arguments, complete results,
  secrets and personal data remain filtered.
- Docker Compose now starts the Next.js web service with the existing one-worker
  FastAPI service.

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
- Container and local execution retain exactly one API worker; queue capacity is
  configurable from 1 to 100 through `ASYNC_RUN_QUEUE_CAPACITY`.
- The local dispatcher accepts an injected provider-client factory at its
  existing provider boundary for deterministic integration verification.
- OpenAPI marks `Idempotency-Key` as required for inquiry, run and retry POST
  commands.
- Commercial result references are resolved through the receipts owned by the
  requested run, preserving retry-attempt isolation.

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
