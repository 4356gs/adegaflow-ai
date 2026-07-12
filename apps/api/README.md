# AdegaFlow AI API

FastAPI backend, Qwen Cloud adapter, SQLite persistence and deterministic commercial tools.

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
