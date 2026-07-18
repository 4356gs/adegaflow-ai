# AdegaFlow AI API

FastAPI backend, Qwen Cloud adapter, SQLite persistence, structured inquiry
analysis, bounded recommendation orchestration, deterministic EUR quotes and
reviewable commercial artifacts.

## Requirements

- Python 3.12+
- Qwen Cloud API key only for live provider tests and later live runs

## Installation

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./apps/api[dev]"
cp .env.example .env
```

## Database and demo data

```bash
make db-upgrade
make seed-demo
```

The seed command is idempotent. To restore canonical demo values:

```bash
make seed-demo-reset
```

The reset command deletes the current MVP demo tables before loading the fixed dataset.

## Execution

```bash
make run-api
```

Endpoints currently exposed:

- `GET /health`
- `GET /api/v1/health`
- OpenAPI: `/docs`

The catalog, stock and customer-history tools are implemented as typed application services. They are not exposed through temporary HTTP endpoints because the approved architecture places them behind the later orchestrator and API contracts.

## Structured inquiry analysis

`InquiryAnalysisService`:

- loads the versioned `inquiry_analysis.v1` prompt;
- requests JSON Object mode through the provider-neutral client protocol;
- validates the response with Pydantic;
- computes missing fields deterministically;
- persists only validated extraction data;
- marks provider or schema failures with safe application errors.

The analysis service is not exposed through a temporary endpoint. It will be invoked by the bounded orchestrator and later by the approved inquiry API.

## Current orchestration boundary

New runs can currently:

- analyze an inquiry;
- retrieve customer history;
- select and validate products through the closed read-tool registry;
- calculate and persist one deterministic EUR quote;
- generate and persist a proposal and email draft;
- finish in `needs_review` with ordered events and summarized references.

CRM opportunity creation, follow-up creation and memory writes remain deferred
to Sprint 2 Block 7. HTTP orchestration endpoints remain deferred to Block 8.

## Quality

```bash
make check-api
```

## Persistence configuration

- `DATABASE_URL` — defaults to `sqlite:///./data/adegaflow.db`
- `DEMO_SEED_PATH` — defaults to `data/seeds/demo_seed.json`

SQLite is the accepted MVP store. The repository layer isolates tool logic from direct engine access and preserves a future PostgreSQL migration path.

## Qwen Cloud

The client uses the OpenAI-compatible endpoint configured with:

- `DASHSCOPE_API_KEY`
- `QWEN_BASE_URL`
- `QWEN_MODEL`
- `QWEN_FALLBACK_MODEL`
- `QWEN_TIMEOUT_SECONDS`
- `QWEN_MAX_RETRIES`

The application can start without a key. Live provider calls fail with a typed, safe configuration error.
