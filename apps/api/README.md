# AdegaFlow AI API

FastAPI backend, Qwen Cloud adapter, SQLite persistence, structured inquiry
analysis, bounded recommendation orchestration, deterministic EUR quotes and
reviewable commercial artifacts with deterministic internal actions.

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
- `POST/GET /api/v1/inquiries`
- `GET /api/v1/inquiries/{inquiry_id}`
- `POST /api/v1/inquiries/{inquiry_id}/agent-runs`
- `GET /api/v1/agent-runs`
- `GET /api/v1/agent-runs/{agent_run_id}`
- `GET /api/v1/agent-runs/{agent_run_id}/events`
- `GET /api/v1/agent-runs/{agent_run_id}/result`
- `POST /api/v1/agent-runs/{agent_run_id}/retry`
- `GET /api/v1/opportunities/{opportunity_id}`
- `GET /api/v1/customers/{customer_id}/memory`
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
- resolve or create the minimum valid customer;
- persist one deterministically qualified CRM opportunity;
- create a pending follow-up exactly seven days later;
- save only explicit, allowed customer-memory facts;
- finish in `needs_review` with ordered events and summarized references.

The three internal actions use canonical fingerprints and persistent receipts,
and commit atomically with their audit trail and terminal run state. The HTTP
layer persists a queued run before dispatch and never holds the request open
while Qwen executes.

`Idempotency-Key` is required for inquiry creation, run creation and retry.
`ASYNC_RUN_QUEUE_CAPACITY` defaults to 10 and accepts values from 1 to 100. The
dispatcher is local and non-durable, so this MVP must use exactly one Uvicorn
worker. Artifact approval, frontend and external actions remain outside the
block.

## Quality

```bash
make check-api
```

Deterministic Block 9 demonstrations:

```bash
make demo-backend
make demo-backend-retry
```

They run through HTTP and the real one-consumer dispatcher using a temporary
SQLite database. Only the Qwen provider boundary is replaced. The live Qwen
smoke remains manual and optional:

```bash
pytest apps/api/tests -m live_qwen -q
```

## Persistence configuration

- `DATABASE_URL` — defaults to `sqlite:///./data/adegaflow.db`
- `DEMO_SEED_PATH` — defaults to `data/seeds/demo_seed.json`
- `ASYNC_RUN_QUEUE_CAPACITY` — defaults to `10`, maximum `100`

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
