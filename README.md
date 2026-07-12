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
- Next block — Bounded orchestration and recommendation

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

The read tools and structured inquiry-analysis service are currently application services. HTTP endpoints and the bounded tool registry enter in later Sprint 2 blocks.

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
