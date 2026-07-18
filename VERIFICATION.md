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

The implementation and its validation evidence remain pending. The Block 7
quality baseline is unchanged. The known non-blocking Starlette TestClient
warning remains unchanged.

## Current target-repository verification

```bash
make check-api
```

The latest combined verification passed on the Block 7 implementation branch.
Docker behavior was not changed by Block 7.
