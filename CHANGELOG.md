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

### Changed

- Product model now records recommended commercial channels in addition to markets.
- Project status reflects the approved Qwen live spike.
- Project status now records Sprint 2 Block 5 as implemented and verified.

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
