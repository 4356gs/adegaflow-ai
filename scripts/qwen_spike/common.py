"""Shared helpers for Qwen Cloud spike scripts."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.ai.qwen_client import QwenClient, QwenClientError  # noqa: E402
from app.core.config import Settings  # noqa: E402

T = TypeVar("T")


def client() -> QwenClient:
    return QwenClient(settings=Settings())


def run_case(name: str, operation: Callable[[], T]) -> T:
    print(f"\n=== {name} ===")
    started = time.perf_counter()
    try:
        result = operation()
    except QwenClientError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        print(
            json.dumps(
                {
                    "status": "failed",
                    "elapsed_ms": elapsed_ms,
                    "error": exc.info.model_dump(mode="json"),
                },
                indent=2,
            )
        )
        raise
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    print(json.dumps({"status": "passed", "elapsed_ms": elapsed_ms}, indent=2))
    return result


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def invalid_credential_test_enabled() -> bool:
    return os.getenv("QWEN_TEST_INVALID_CREDENTIAL", "").lower() in {"1", "true", "yes"}
