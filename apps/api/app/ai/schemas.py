"""Provider-neutral schemas for Qwen model turns."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Usage(BaseModel):
    """Token usage returned by the provider when available."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ToolCall(BaseModel):
    """Normalized tool request."""

    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str

    def as_openai_dict(self) -> dict[str, Any]:
        """Serialize the tool call for a subsequent Chat Completions request."""

        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.raw_arguments,
            },
        }


class ModelTurn(BaseModel):
    """Normalized assistant response independent of the SDK object model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    content: str | None = None
    finish_reason: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)

    def as_assistant_message(self) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": "assistant",
            "content": self.content or "",
        }
        if self.tool_calls:
            message["tool_calls"] = [call.as_openai_dict() for call in self.tool_calls]
        return message


class QwenErrorInfo(BaseModel):
    """Safe provider error returned to callers."""

    code: str
    message: str
    retryable: bool
    category: Literal[
        "configuration",
        "authentication",
        "timeout",
        "rate_limit",
        "provider",
        "invalid_response",
        "unexpected",
    ]
