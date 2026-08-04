# Verification Report

Date: 2026-07-18

## Qwen Cloud gate

| Check | Result |
|---|---|
| S-01 basic call | Passed |
| S-02 structured output with Pydantic validation | Passed |
| S-03 function calling | Passed |
| S-04 tool roundtrip | Passed |
| Missing-key error case | Passed |
| Invalid-credential case | Pending explicit execution |

## Repository baseline after PR #1

| Check | Result |
|---|---|
| Ruff | Passed |
| mypy strict | Passed, 29 source files |
| pytest | Passed, 23 tests |
| Alembic upgrade | Passed |
| Seed second execution | Passed without duplicates |

## Structured inquiry-analysis package

The Block 4 implementation was validated in an isolated reconstruction before handoff:

| Check | Result |
|---|---|
| Ruff on new block | Passed |
| mypy strict on reconstructed API package | Passed |
| Block 4 pytest suite | Passed, 7 tests |
| Primary German inquiry persistence | Passed |
| Deterministic missing fields | Passed |
| Invalid payload failure state | Passed |
| Provider timeout failure state | Passed |
| Packaged versioned prompt | Passed |

## Bounded orchestration and recommendation — Block 5

Block 5 was verified on `main` after merging PR #3.

| Check | Result |
|---|---|
| Merge commit | `1b94b4c` |
| Ruff | Passed |
| mypy strict | Passed, 39 source files |
| pytest excluding live Qwen | Passed, 60 tests |
| API CI | Passed |
| Working tree | Clean |
| Quotes, CRM, follow-up, API and frontend | Not implemented |

One non-blocking `StarletteDeprecationWarning` was emitted by the test-client
dependency. No dependency changes were introduced as part of the Block 5
closeout.

## Deterministic quote and reviewable artifacts — Block 6

Block 6 was verified on `main` after merging PR #6.

| Check | Result |
|---|---|
| Merge commit | `69ec1ee` |
| Ruff | Passed |
| mypy strict | Passed, 44 source files |
| pytest excluding live Qwen | Passed, 85 tests |
| Total coverage | 92% |
| Working tree | Clean |
| Quote currency and arithmetic | Deterministic EUR integer cents |
| Proposal and email draft | Persisted with `needs_review` |
| CRM, follow-up, memory writes, API and frontend | Not implemented |

The known non-blocking Starlette TestClient warning remains unchanged.

## Deterministic internal actions — Block 7

Block 7 was verified on `feat/sprint2-internal-actions` from baseline
`2cb343b`.

| Check | Result |
|---|---|
| Ruff | Passed |
| mypy strict | Passed, 48 source files |
| pytest excluding live Qwen | Passed, 102 tests |
| Branch coverage | 89.82% |
| Alembic `0003 → 0004 → 0003 → 0004` | Passed |
| CRM opportunity | Deterministic and limited to one per inquiry |
| Follow-up | Pending, exactly seven days from injected UTC clock |
| Customer memory | Explicit, limited, normalized and deduplicated |
| Receipts | Three canonical SHA-256 idempotency records |
| Atomic rollback | Verified for an intermediate persistence failure |
| Qwen calls during internal actions | None |
| Inventory mutation | None |
| API, background tasks, frontend and external integrations | Not implemented |

The known non-blocking Starlette TestClient warning remains unchanged.

## Block 8 documentation review

Block 8 was planned from `main` at `644d12f` without changing product code.

| Check | Result |
|---|---|
| ADR-014 | Accepted for MVP |
| Binding plan | `docs/implementation/064-api-and-async-execution.md` |
| API contract | Versioned inquiries, runs, polling, result and retry |
| Async boundary | One in-process consumer; no durable queue |
| Restart policy | `RUN_INTERRUPTED` plus explicit retry |
| Retry ownership | New run linked by `retry_of_run_id` |
| HTTP idempotency | Persistent keys for inquiry, run and retry commands |
| Artifact approval, frontend and external writes | Excluded |
| `git diff --check` | Passed |
| Ruff | Passed |
| mypy strict | Passed, 48 source files |
| pytest excluding live Qwen | Passed, 102 tests |

## HTTP API and asynchronous execution — Block 8

Block 8 was implemented from `ffdf2eae` on
`feat/sprint2-async-run-api`.

| Check | Result |
|---|---|
| Alembic `base → 0005 → 0004 → 0005` | Passed on SQLite |
| Persistent HTTP idempotency | Inquiry, run and retry commands verified |
| Dispatcher | Bounded FIFO queue, one consumer and independent worker sessions |
| Restart recovery | Active runs and started tools close with `RUN_INTERRUPTED` |
| Retry | New linked run; original remains immutable |
| Route boundary | Product endpoints only under `/api/v1`; health only at `/health` |
| OpenAPI | Required paths, schemas and error responses verified |
| Ruff | Passed |
| mypy strict | Passed, 53 source files |
| pytest excluding live Qwen | Passed, 114 tests |
| Total coverage | 90% |
| Frontend, approvals, external actions and durable queue | Not implemented |

The known non-blocking Starlette TestClient warning remains unchanged.

## Backend verification and Sprint 2 closure — Block 9

Block 9 was reconstructed from baseline
`412543258ae3960a265141427ad27873dfce1fc7` on
`test/sprint2-backend-closeout`.

| Check | Result |
|---|---|
| Complete Qwen provider mock | Passed; analysis, tools, recommendation, proposal and email |
| HTTP + real dispatcher + temporary SQLite E2E | Passed |
| Happy path, three POST idempotency limits and polling | Passed |
| Expanded authoritative result | Passed |
| Retry creates a new run and preserves original | Passed |
| Second session active-memory recovery | Passed |
| Opportunity/follow-up/memory non-duplication | Passed |
| `make demo-backend` | Passed |
| `make demo-backend-retry` | Passed |
| pytest excluding live Qwen | Passed, 125 tests |
| Branch coverage | 90% |
| Ruff | Passed |
| mypy strict | Passed, 53 source files |
| Migrations and reproducible seeds on temporary SQLite | Passed |
| Docker declaration | One Uvicorn worker, healthcheck and bounded queue verified |
| Docker image build | Passed |
| Docker migration and canonical seed | Passed |
| Docker service health | Passed; Compose reported `healthy` and `/health` returned the expected payload |
| Docker effective process | Passed with exactly one Uvicorn worker |
| Live Qwen | Not run; optional and non-blocking |

Detailed AT and B9 traceability is recorded in
`docs/implementation/066-sprint-2-closure.md`. All Block 9 verification gates
passed. PR #12 was merged into `main` at
`3f518e67b5ca24f7749abe0f0783a25e05639783`, and the complete quality, demo and
Docker verification was repeated successfully on that clean merge commit.
Sprint 2 is closed.

## Current target-repository verification

```bash
make check-api
```

The latest combined verification passed on the Block 9 closeout branch. Docker
is fixed to one Uvicorn worker and exposes the bounded queue capacity setting.

## Sprint 3 Block 1 — web foundation candidate

Baseline: `8ebf0b29be9e4aa81605d090c259c5a4823f724f`.

| Check | Result |
|---|---|
| ESLint | Passed with zero warnings |
| TypeScript strict | Passed |
| Frontend contract/unit tests | Passed, 22 tests |
| Backend suite excluding live Qwen | Passed, 130 tests |
| Ruff | Passed |
| mypy strict | Passed, 53 source files |
| Next.js production build | Passed |
| Backend `tool_name` safe contract | Added for start, success, failure and rejection |
| Browser access | Same-origin routes only |
| FastAPI URL | Server-only `FASTAPI_BASE_URL` |
| Docker topology | Web depends on healthy API; API remains one worker |
| Browser bundle | No internal FastAPI URL or `FASTAPI_BASE_URL` |
| Local integrated smoke | `/`, `/api/health` and `/api/v1/agent-runs` passed through Next.js → FastAPI → SQLite |

Compose and the combined backend/frontend gate must be executed before the
block is declared closed.
