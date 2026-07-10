"""Qwen Cloud adapter using the OpenAI-compatible Chat Completions API."""

import json
from collections.abc import Sequence
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.ai.schemas import ModelTurn, QwenErrorInfo, ToolCall, Usage
from app.core.config import Settings, get_settings

Message = dict[str, Any]
ToolDefinition = dict[str, Any]


class QwenClientError(RuntimeError):
    """Typed, safe error raised by the Qwen adapter."""

    def __init__(self, info: QwenErrorInfo) -> None:
        super().__init__(info.message)
        self.info = info


class QwenNotConfiguredError(QwenClientError):
    """Raised when a live call is requested without an API key."""


class QwenClient:
    """Small provider boundary used by spike scripts and later orchestration."""

    def __init__(
        self,
        settings: Settings | None = None,
        sdk_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._sdk_client = sdk_client

    @property
    def configured(self) -> bool:
        return self.settings.qwen_configured

    def _client(self) -> Any:
        if self._sdk_client is not None:
            return self._sdk_client

        if not self.settings.qwen_configured:
            raise QwenNotConfiguredError(
                QwenErrorInfo(
                    code="QWEN_NOT_CONFIGURED",
                    message="Qwen Cloud API key is not configured.",
                    retryable=False,
                    category="configuration",
                )
            )

        assert self.settings.dashscope_api_key is not None
        self._sdk_client = OpenAI(
            api_key=self.settings.dashscope_api_key.get_secret_value(),
            base_url=self.settings.qwen_base_url,
            timeout=float(self.settings.qwen_timeout_seconds),
            max_retries=self.settings.qwen_max_retries,
        )
        return self._sdk_client

    def complete_text(
        self,
        messages: Sequence[Message],
        *,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> ModelTurn:
        return self._create(
            messages=messages,
            model=model,
            temperature=temperature,
        )

    def complete_json(
        self,
        messages: Sequence[Message],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]:
        """Request JSON Object mode, validate it, and repair it once if needed."""

        def parse_and_validate(content: str | None) -> dict[str, Any]:
            if not content:
                raise ValueError("Model returned empty content in JSON mode.")

            payload = json.loads(content)

            if not isinstance(payload, dict):
                raise TypeError("JSON output must be an object.")

            if schema is None:
                return payload

            validated = schema.model_validate(payload)
            return validated.model_dump(mode="json")

        turn = self._create(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        try:
            return parse_and_validate(turn.content), turn
        except (
            json.JSONDecodeError,
            ValidationError,
            TypeError,
            ValueError,
        ) as initial_error:
            if schema is None:
                raise self._invalid_response(
                    "Model returned invalid JSON."
                ) from initial_error

            if isinstance(initial_error, ValidationError):
                validation_errors: object = initial_error.errors(
                    include_url=False
                )
            else:
                validation_errors = [
                    {
                        "type": initial_error.__class__.__name__,
                        "message": str(initial_error),
                    }
                ]

            repair_messages: list[Message] = [
                {
                    "role": "system",
                    "content": (
                        "Repair the supplied JSON so it conforms exactly to the "
                        "provided JSON Schema. Return only one JSON object. "
                        "Use exactly the schema property names. "
                        "Include every property listed as required. "
                        "Do not add properties. "
                        "For an unknown nullable field, use null. "
                        "For an unknown array field, use an empty array."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "JSON Schema:\n"
                        + json.dumps(
                            schema.model_json_schema(),
                            ensure_ascii=False,
                        )
                        + "\n\nValidation errors:\n"
                        + json.dumps(
                            validation_errors,
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n\nInvalid JSON:\n"
                        + (turn.content or "")
                    ),
                },
            ]

            repair_turn = self._create(
                messages=repair_messages,
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            try:
                repaired_payload = parse_and_validate(repair_turn.content)
            except (
                json.JSONDecodeError,
                ValidationError,
                TypeError,
                ValueError,
            ) as repair_error:
                raise self._invalid_response(
                    "JSON output does not conform to the schema after repair."
                ) from repair_error

            return repaired_payload, repair_turn

    def request_tools(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ToolDefinition],
        tool_choice: str | dict[str, Any] = "auto",
        model: str | None = None,
    ) -> ModelTurn:
        return self._create(
            messages=messages,
            model=model,
            tools=list(tools),
            tool_choice=tool_choice,
            temperature=0.1,
        )

    def _create(
        self,
        *,
        messages: Sequence[Message],
        model: str | None,
        temperature: float,
        tools: Sequence[ToolDefinition] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, str] | None = None,
    ) -> ModelTurn:
        kwargs: dict[str, Any] = {
            "model": model or self.settings.qwen_model,
            "messages": list(messages),
            "temperature": temperature,
            "extra_body": {"enable_thinking": False},
        }
        if tools is not None:
            kwargs["tools"] = list(tools)
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            completion = self._client().chat.completions.create(**kwargs)
            return self._normalize(completion)
        except QwenClientError:
            raise
        except AuthenticationError as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code="QWEN_AUTHENTICATION_FAILED",
                    message="Qwen Cloud rejected the configured credentials.",
                    retryable=False,
                    category="authentication",
                )
            ) from exc
        except APITimeoutError as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code="QWEN_TIMEOUT",
                    message="Qwen Cloud did not respond before the timeout.",
                    retryable=True,
                    category="timeout",
                )
            ) from exc
        except RateLimitError as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code="QWEN_RATE_LIMITED",
                    message="Qwen Cloud rate limit was reached.",
                    retryable=True,
                    category="rate_limit",
                )
            ) from exc
        except APIConnectionError as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code="QWEN_CONNECTION_FAILED",
                    message="Could not connect to Qwen Cloud.",
                    retryable=True,
                    category="provider",
                )
            ) from exc
        except APIStatusError as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code=f"QWEN_HTTP_{exc.status_code}",
                    message="Qwen Cloud returned an API error.",
                    retryable=exc.status_code >= 500,
                    category="provider",
                )
            ) from exc
        except Exception as exc:
            raise QwenClientError(
                QwenErrorInfo(
                    code="QWEN_UNEXPECTED_ERROR",
                    message="Unexpected error while calling Qwen Cloud.",
                    retryable=False,
                    category="unexpected",
                )
            ) from exc

    @staticmethod
    def _normalize(completion: Any) -> ModelTurn:
        if not getattr(completion, "choices", None):
            raise QwenClient._invalid_response("Provider response contains no choices.")

        choice = completion.choices[0]
        message = choice.message
        normalized_calls: list[ToolCall] = []

        for call in getattr(message, "tool_calls", None) or []:
            raw_arguments = call.function.arguments or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise QwenClient._invalid_response("Tool arguments are not valid JSON.") from exc
            if not isinstance(arguments, dict):
                raise QwenClient._invalid_response("Tool arguments must be a JSON object.")
            normalized_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                    raw_arguments=raw_arguments,
                )
            )

        sdk_usage = getattr(completion, "usage", None)
        usage = Usage(
            prompt_tokens=getattr(sdk_usage, "prompt_tokens", None),
            completion_tokens=getattr(sdk_usage, "completion_tokens", None),
            total_tokens=getattr(sdk_usage, "total_tokens", None),
        )

        return ModelTurn(
            model=getattr(completion, "model", "unknown"),
            content=getattr(message, "content", None),
            finish_reason=getattr(choice, "finish_reason", None),
            tool_calls=normalized_calls,
            usage=usage,
        )

    @staticmethod
    def _invalid_response(message: str) -> QwenClientError:
        return QwenClientError(
            QwenErrorInfo(
                code="QWEN_INVALID_RESPONSE",
                message=message,
                retryable=True,
                category="invalid_response",
            )
        )
