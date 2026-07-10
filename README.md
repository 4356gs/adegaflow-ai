# AdegaFlow AI

Autonomous commercial opportunity agent for Galician wineries, built for the Qwen Cloud Hackathon.

## Current status

- Sprint 0 — Product definition: **complete**
- Sprint 1 — Architecture: **complete**
- Sprint 2 documentation: **complete**
- Sprint 2 Block 0 — API bootstrap: **implemented**
- Sprint 2 Block 1 — Qwen spike code: **implemented**
- Qwen live verification: **pending API key**

No claim is made that the external Qwen integration has passed until the live spike is executed.

## Architecture baseline

- Next.js + TypeScript — planned for Sprint 3
- FastAPI + Python — bootstrapped
- Qwen Cloud `qwen3.7-plus`
- `qwen3.6-flash` fallback
- OpenAI-compatible Chat Completions
- SQLite — next implementation block
- Docker Compose
- Alibaba Cloud ECS — deployment target

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./apps/api[dev]"
cp .env.example .env
make check-api
make run-api
```

Open:

- API health: `http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/docs`

## Qwen spike

Add `DASHSCOPE_API_KEY` to your local environment, then:

```bash
make qwen-spike
```

Results are recorded in `scripts/qwen_spike/results.md`.

## Docker

```bash
docker compose up --build api
```

## Repository

```text
apps/api/                 FastAPI service
scripts/qwen_spike/       External integration gate
docs/                     Product, architecture, ADR, hackathon, implementation
data/                     Reserved for demo data
infra/                    Reserved for Alibaba Cloud deployment
```

## Governance

The documentation under `docs/` is the source of truth. The next implementation block is domain persistence and demo seeds, but it must not start before the live Qwen gate is approved.

## License

MIT.
