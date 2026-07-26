# AdegaFlow AI

Autonomous commercial opportunity agent for Galician wineries, built for the Qwen Cloud Hackathon.

## Current status

- Sprint 0 — Product definition: **complete**
- Sprint 1 — Architecture: **complete**
- Sprint 2 documentation: **complete**
- Sprint 2 Block 0 — API bootstrap: **implemented**
- Sprint 2 Block 1 — Qwen spike: **approved (S-01 to S-04)**
- Sprint 2 Block 2 — SQLite persistence and reproducible seeds: **implemented**
- Sprint 2 Block 3 — Read tools: **implemented**
- Sprint 2 Block 4 — Structured inquiry analysis: **implemented**
- Sprint 2 Block 5 — Bounded orchestration and recommendation: **implemented**
- Sprint 2 Block 6 — Deterministic quote and reviewable artifacts: **implemented**
- Sprint 2 Block 7 — Deterministic internal actions: **implemented**
- Sprint 2 Block 8 — HTTP API and asynchronous execution: **implemented**
- Sprint 2 Block 9 — Backend verification and closeout: **verified**
- Next gate — review, commit, PR, merge and clean `main` revalidation

The frontend remains intentionally deferred until the backend contract and critical acceptance scenarios are stable.

## Architecture baseline

- Next.js + TypeScript — planned for Sprint 3
- FastAPI + Python
- Qwen Cloud `qwen3.7-plus`
- `qwen3.6-flash` fallback
- OpenAI-compatible Chat Completions
- SQLite + SQLAlchemy 2.0 + Alembic
- Docker Compose
- Alibaba Cloud ECS — deployment target

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./apps/api[dev]"
cp .env.example .env
make db-upgrade
make seed-demo
make check-api
make run-api
```

Open:

- API health: `http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/docs`

The backend is invocable under `/api/v1`: clients can submit and inspect
inquiries, create asynchronous agent runs, poll state and ordered events, read
terminal commercial results and explicitly retry recoverable failures. POST
commands use persistent idempotency keys.

The local dispatcher has one bounded in-process queue and exactly one consumer.
It is intentionally non-durable: process restarts close interrupted work with
`RUN_INTERRUPTED`, after which a client may create an audited retry run. Run the
MVP with one Uvicorn worker. Frontend, artifact approval and external actions
remain deferred.

## Reproducible backend demos

The mandatory closeout demonstrations use a complete Qwen provider mock and a
temporary migrated SQLite database. They do not use network access or a Qwen
API key:

```bash
make demo-backend
make demo-backend-retry
```

The first command covers the happy path, idempotency, polling, expanded result,
commercial-action counts and a second buyer session. The second covers a typed
provider timeout, immutable original run and explicit retry.

## Database operations

```bash
make db-upgrade
make db-downgrade
make seed-demo
make seed-demo-reset
```

`seed-demo-reset` is destructive for the current MVP demo tables. Do not use it against a non-demo database.

## Qwen spike

Add `DASHSCOPE_API_KEY` to your local `.env`, then:

```bash
make qwen-spike
```

Results are recorded in `scripts/qwen_spike/results.md`.

## Docker

```bash
docker compose up --build api
```

SQLite runtime data is stored in the named volume `adegaflow-data`. Demo seed files are mounted read-only from `data/seeds`.

## Repository

```text
apps/api/                 FastAPI service, persistence, prompts and tools
scripts/qwen_spike/       External integration gate
docs/                    Product, architecture, ADR, hackathon, implementation
data/seeds/              Reproducible fictitious demo dataset
infra/                   Reserved for Alibaba Cloud deployment
```

## Governance

The documentation under `docs/` is the source of truth. No frontend work starts until the backend gate defined in the Sprint 2 Definition of Done is met.

## License

MIT.
