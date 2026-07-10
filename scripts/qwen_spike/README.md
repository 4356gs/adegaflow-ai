# Qwen Cloud Integration Spike

These scripts validate the external dependency before the agent core is built.
They do not write to the application database and do not contain secrets.

## Prerequisites

```bash
python -m pip install -e "./apps/api[dev]"
cp .env.example .env
export DASHSCOPE_API_KEY="..."
```

The scripts read environment variables directly. A root `.env` file is used by
application settings when commands are executed from the repository root.

## Run

```bash
python scripts/qwen_spike/01_basic_call.py
python scripts/qwen_spike/02_structured_output.py
python scripts/qwen_spike/03_single_tool_call.py
python scripts/qwen_spike/04_tool_roundtrip.py
python scripts/qwen_spike/05_error_handling.py
```

Or:

```bash
make qwen-spike
```

## Safety

- The API key is never printed.
- Thinking mode is disabled.
- JSON output is validated with Pydantic.
- The error script tests missing configuration locally; it does not deliberately
  send an invalid credential unless `QWEN_TEST_INVALID_CREDENTIAL=true` is set.
- Results must be recorded in `results.md` without secrets or full HTTP headers.
