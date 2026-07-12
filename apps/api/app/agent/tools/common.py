"""Common response envelope for deterministic agent tools."""

from time import perf_counter_ns
from typing import TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")
TOOL_VERSION = "1.0"


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ToolMeta(BaseModel):
    tool_version: str = TOOL_VERSION
    duration_ms: int = Field(ge=0)


class ToolResponse[DataT](BaseModel):
    success: bool
    data: DataT | None
    error: ToolError | None
    meta: ToolMeta


def started_timer() -> int:
    return perf_counter_ns()


def elapsed_ms(started_ns: int) -> int:
    return max(0, (perf_counter_ns() - started_ns) // 1_000_000)
