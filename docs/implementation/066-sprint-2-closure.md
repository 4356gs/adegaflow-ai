# Sprint 2 — Backend verification and closure candidate

- **Date:** 2026-07-26
- **Baseline:** `412543258ae3960a265141427ad27873dfce1fc7`
- **Branch:** `test/sprint2-backend-closeout`
- **Implementation commit:** pending
- **Status:** verified closure candidate; review and merge pending

## Outcome

Sprint 2 Block 9 verifies UC-001 through HTTP with a complete Qwen provider
mock while keeping FastAPI, the one-consumer dispatcher, services, tools,
repositories, SQLite and public read models real. The deterministic suite does
not require network access or `DASHSCOPE_API_KEY`.

The implementation also corrects two verified contract divergences:

1. OpenAPI now marks `Idempotency-Key` as required on all three POST commands.
2. Run results and references resolve opportunity and follow-up through the
   receipts owned by that run. A successful retry can no longer make the
   original failed run appear to own the retry's commercial actions.

No route, public response schema, product capability or architecture was
expanded.

## Acceptance scenarios AT-001 to AT-020

| Acceptance | Result | Primary evidence |
|---|---|---|
| AT-001 | Passed | `test_http_dispatcher_happy_path_idempotency_and_second_session` |
| AT-002 | Passed | `test_missing_fields_are_computed_deterministically` |
| AT-003 | Passed | `test_rejects_insufficient_stock` |
| AT-004 | Passed | `test_unknown_identifiable_buyer_gets_minimal_customer_without_matching` |
| AT-005 | Passed | Qwen JSON repair tests and safe HTTP envelopes |
| AT-006 | Passed | unknown-tool and registry allowlist tests |
| AT-007 | Passed | provider timeout and retry E2E |
| AT-008 | Passed | internal-action idempotency plus happy E2E counts |
| AT-009 | Passed | second-session active-memory assertion in happy E2E |
| AT-010 | Passed | atomic internal-action rollback tests |
| AT-011 | Passed | bounded model/tool-limit tests |
| AT-012 | Passed | public event filtering and safe error tests |
| AT-013 | Passed | complete orchestration and happy E2E |
| AT-014 | Passed | partial-result and non-terminal result tests |
| AT-015 | Passed | queued-before-enqueue, polling and ordered cursor tests |
| AT-016 | Passed | three idempotent POST commands and conflicts |
| AT-017 | Passed | interrupted-run recovery test |
| AT-018 | Passed | closed retry policy and retry E2E |
| AT-019 | Passed | authoritative expanded result and strict contracts |
| AT-020 | Passed | OpenAPI route-prefix contract |

## B9 traceability

Existing tests are reused where they already satisfy the row. No test was
duplicated merely to adopt a B9 name.

| B9 ID | Test file and test |
|---|---|
| B9-U01 | `test_internal_actions.py::test_internal_actions_are_atomic_traceable_and_idempotent`; `test_changed_followup_fingerprint_is_rejected_without_overwrite` |
| B9-U02 | `test_async_dispatcher.py::test_retry_policy_is_closed` |
| B9-U03 | `test_http_async_api.py::test_failed_run_does_not_borrow_commercial_actions_from_another_run`; happy E2E |
| B9-U04 | `test_http_async_api.py::test_public_events_filter_secrets_and_raw_provider_payloads` |
| B9-U05 | `test_http_async_api.py::test_event_cursor_has_no_gaps_or_duplicates` |
| B9-C01 | `test_http_async_api.py::test_openapi_has_only_documented_product_prefixes` |
| B9-C02 | `test_http_async_api.py::test_openapi_requires_idempotency_header_on_all_commands` |
| B9-C03 | `test_http_async_api.py::test_public_contract_rejects_extras_invalid_uuid_and_query_limits` |
| B9-C04 | `test_http_async_api.py::test_missing_key_and_validation_use_safe_error_envelope` |
| B9-C05 | `test_http_async_api.py::test_run_is_committed_before_enqueue_and_not_duplicated`; `test_terminal_partial_result_and_commercial_reads` |
| B9-I01 | `test_fake_qwen.py::test_fake_qwen_covers_analysis_tools_recommendation_and_artifacts`; happy E2E |
| B9-I02 | `test_async_dispatcher.py::test_dispatcher_lifecycle_starts_and_stops_one_consumer`; `test_dispatcher_uses_injected_client_factory_per_run` |
| B9-I03 | `test_http_async_api.py::test_inquiry_create_is_idempotent_and_versioned`; `test_run_is_committed_before_enqueue_and_not_duplicated` |
| B9-I04 | `test_internal_actions.py::test_failure_during_followup_rolls_back_entire_action_unit`; `test_bounded_orchestration.py::test_internal_action_conflict_rolls_back_and_preserves_artifacts` |
| B9-I05 | `test_http_async_api.py::test_interrupted_run_can_retry_without_mutating_original`; retry E2E |
| B9-I06 | `test_http_async_api.py::test_event_cursor_has_no_gaps_or_duplicates`; happy E2E |
| B9-I07 | happy E2E and `test_failed_run_does_not_borrow_commercial_actions_from_another_run` |
| B9-I08 | happy E2E second session; `test_read_tools.py::test_retrieve_customer_history_returns_only_active_memories` |
| B9-I09 | `test_qwen_client.py::test_narrative_json_is_repaired_once`; `test_invalid_narrative_after_repair_is_typed_error` |
| B9-I10 | `test_bounded_orchestration.py::test_unknown_tool_never_executes_and_finishes_needs_review`; model/tool-limit tests |
| B9-I11 | `test_recommendation_validation.py::test_rejects_insufficient_stock` |
| B9-I12 | `test_internal_actions.py::test_unknown_identifiable_buyer_gets_minimal_customer_without_matching` |
| B9-I13 | `test_inquiry_analysis.py::test_missing_fields_are_computed_deterministically` |
| B9-E01 | `test_backend_closeout_e2e.py::test_http_dispatcher_happy_path_idempotency_and_second_session` |
| B9-E02 | happy E2E replays inquiry and run POST commands |
| B9-E03 | happy E2E verifies one opportunity, one follow-up and three receipts per run |
| B9-E04 | `test_backend_closeout_e2e.py::test_http_retry_creates_new_run_and_keeps_original_immutable` |
| B9-E05 | happy E2E creates a second inquiry and verifies active-memory recovery |
| B9-D01 | `test_docker_contract.py::test_docker_contract_declares_one_worker_healthcheck_volume_and_bounded_queue`; Docker Desktop runtime verification passed |
| B9-L01 | Optional; not executed |

## Demo evidence

### `make demo-backend`

The runner creates a temporary database, migrates it to
`0005_http_async_runs`, loads the canonical seed, starts the application
lifespan with the real dispatcher and executes the public HTTP flow.

Observed assertions:

- inquiry `201`, equivalent replay `200`;
- run and equivalent replay `202` with the same run ID;
- 48 ordered events read with cursors until `needs_review`;
- quote total `609000` EUR cents and two reviewable artifacts;
- exactly one opportunity, one follow-up, three receipts and five active
  buyer memories after the first session;
- second session recovers active memory and excludes the inactive seed fact;
- inventory is unchanged.

### `make demo-backend-retry`

Observed assertions:

- first run fails with safe `QWEN_TIMEOUT` and `retryable=true`;
- retry POST returns `202` and a different run ID;
- `retry_of_run_id` references the original;
- equivalent retry key returns the same retry run;
- retry reaches `needs_review`;
- original detail and events remain byte-equivalent at the public boundary;
- original result owns no opportunity or follow-up created by the retry.

Both runners return non-zero if an assertion fails and require neither network
nor a provider secret.

## Database verification

The required destructive checks use only an explicitly named temporary SQLite
file.

| Check | Result |
|---|---|
| `base → 0005` | Passed |
| `0005 → 0004 → 0005` | Passed |
| seed first and second execution | Same canonical counts |
| seed reset | Canonical values restored |

## Quality evidence

| Gate | Result |
|---|---|
| Ruff | Passed |
| mypy strict | Passed in 53 application files |
| pytest excluding `live_qwen` | 125 passed |
| Branch coverage | 90%, gate ≥80% |
| `git diff --check` | Passed |
| Known warning | One non-blocking Starlette TestClient deprecation warning |
| Live Qwen | Not run; optional and non-blocking |
| Docker static contract | Passed |
| Docker build | Passed with `adegaflow-ai-api:latest` |
| Docker migration | Passed through `0005_http_async_runs` |
| Docker seed | Passed with canonical seed counts |
| Docker health | Passed; Compose reported `healthy` and `/health` returned the expected service payload |
| Docker effective process | Passed; Uvicorn ran with exactly `--workers 1` |

B9-D01 was executed successfully on Ubuntu 24.04 under WSL 2 with Docker
Desktop 4.83.0, Engine 29.6.2 and Compose 5.3.1. The container was removed
cleanly after the verification.

Sprint 2 must not be declared closed until the implementation is reviewed and
merged, and `main` is reverified.

## Residual risks and exclusions

- The queue remains in-process and non-durable.
- Exactly one API worker is required.
- SQLite is accepted only for this MVP.
- Provider-live compatibility beyond the approved spike is optional here.
- Frontend, artifact approval, external CRM/calendar/email, authentication,
  PostgreSQL, final deployment and hackathon submission remain excluded.
- No Sprint 3 implementation was started.
