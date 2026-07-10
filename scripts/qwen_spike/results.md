# Qwen Cloud Spike Results

- Date: 2026-07-10
- Model: qwen3.7-plus
- Endpoint: international OpenAI-compatible API
- Status: PASSED WITH FOLLOW-UP ACTIONS

## Results

| Test | Result | Latency |
|---|---|---:|
| S-01 Basic call | Passed | 2348 ms |
| S-02 Structured output | Passed | 3701 ms |
| S-03 Single tool call | Passed | 2842 ms |
| S-04 Tool roundtrip | Passed | 6743 ms |
| S-05 Missing key | Passed | N/A |
| S-05 Invalid credential | Pending explicit execution | N/A |

## Confirmed capabilities

- Qwen Cloud authentication
- qwen3.7-plus availability
- JSON Object mode
- Pydantic validation
- Function calling
- Local tool execution
- Tool-result roundtrip
- Token usage reporting
- Controlled missing-key error

## Follow-up actions

1. Compute required missing fields deterministically.
2. Complete invalid-credential test.
3. Add timeout tests with a fake client.
4. Preserve bounded retries and tool-call limits.
5. Do not depend exclusively on model output for business rules.
