# AdegaFlow AI

AI-assisted commercial opportunity workflow for Galician wineries, being
developed as an MVP for customer demonstrations and commercial validation.

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
- Sprint 2 — **closed on `main`**
- Sprint 3 Block 1 — web foundation and contract: **implementation candidate**

The backend contract and critical acceptance scenarios are stable. Block 1 adds
the reproducible web foundation; business screens remain assigned to later
Sprint 3 blocks.

## Architecture baseline

- Next.js 16 + React 19 + strict TypeScript + Tailwind CSS 4
- FastAPI + Python
- Qwen Cloud `qwen3.7-plus`
- `qwen3.6-flash` fallback
- OpenAI-compatible Chat Completions
- SQLite + SQLAlchemy 2.0 + Alembic
- Docker Compose
- Controlled deployment — planned for commercial-validation preparation

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

In a second terminal:

```bash
make install-web
make run-web
```

Open:

- API health: `http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/docs`
- Web shell: `http://localhost:3000`
- API health through the web proxy: `http://localhost:3000/api/health`

The backend is invocable under `/api/v1`: clients can submit and inspect
inquiries, create asynchronous agent runs, poll state and ordered events, read
terminal commercial results and explicitly retry recoverable failures. POST
commands use persistent idempotency keys. The browser uses the same-origin
Next.js proxy; `FASTAPI_BASE_URL` remains server-only.

The local dispatcher has one bounded in-process queue and exactly one consumer.
It is intentionally non-durable: process restarts close interrupted work with
`RUN_INTERRUPTED`, after which a client may create an audited retry run. Run the
MVP with one Uvicorn worker. Artifact approval and external actions remain
deferred.

## Web quality

Node.js 22 and npm are required:

```bash
make check-web
make check
```

The web client centralizes manual TypeScript contracts for the existing P0 API.
No browser bundle receives the FastAPI service URL or Qwen credentials.

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
docker compose up --build
```

Open `http://localhost:3000`. SQLite runtime data is stored in the named volume
`adegaflow-data`; demo seed files are mounted read-only. The API container keeps
exactly one Uvicorn worker.

## Repository

```text
apps/api/            FastAPI service, persistence, prompts and tools
apps/web/            Next.js web shell, proxy and typed HTTP client
scripts/qwen_spike/  External integration gate
docs/               Product, architecture, ADR and implementation source of truth
docs/hackathon/     Historical competition material; not current direction
data/seeds/         Reproducible fictitious demo dataset
infra/              Reserved for controlled deployment work
```

## Governance

The documentation under `docs/` is the source of truth. Sprint 2 is closed.
Sprint 3 implementation does not start until its charter, frontend architecture,
implementation plan and Definition of Done are approved and merged.

## License

MIT.
