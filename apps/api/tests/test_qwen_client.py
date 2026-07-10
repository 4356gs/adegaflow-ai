import json
from types import SimpleNamespace
from typing import Any

import pytest
from app.ai.qwen_client import QwenClient, QwenClientError, QwenNotConfiguredError
from app.core.config import Settings
from pydantic import BaseModel


class FakeCompletions:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return self.response


class FakeSdkClient:
    def __init__(self, response: Any) -> None:
        self.completions = FakeCompletions(response)
        self.chat = SimpleNamespace(completions=self.completions)


def completion(
    *,
    content: str | None = "ok",
    tool_calls: list[Any] | None = None,
    finish_reason: str = "stop",
) -> Any:
    return SimpleNamespace(
        model="qwen3.7-plus",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content, tool_calls=tool_calls),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def tool_call(name: str, arguments: dict[str, Any]) -> Any:
    return SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def test_missing_key_raises_safe_configuration_error() -> None:
    client = QwenClient(settings=Settings(DASHSCOPE_API_KEY=""))

    with pytest.raises(QwenNotConfiguredError) as captured:
        client.complete_text([{"role": "user", "content": "hello"}])

    assert captured.value.info.code == "QWEN_NOT_CONFIGURED"
    assert captured.value.info.retryable is False


def test_text_completion_is_normalized() -> None:
    fake = FakeSdkClient(completion(content="Hello from Qwen"))
    client = QwenClient(settings=Settings(), sdk_client=fake)

    turn = client.complete_text([{"role": "user", "content": "hello"}])

    assert turn.content == "Hello from Qwen"
    assert turn.usage.total_tokens == 15
    assert fake.completions.last_kwargs is not None
    assert fake.completions.last_kwargs["extra_body"] == {"enable_thinking": False}


def test_json_completion_validates_schema() -> None:
    class Payload(BaseModel):
        market: str
        bottles: int

    fake = FakeSdkClient(completion(content='{"market":"DE","bottles":600}'))
    client = QwenClient(settings=Settings(), sdk_client=fake)

    payload, _ = client.complete_json(
        [
            {"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Extract the inquiry."},
        ],
        schema=Payload,
    )

    assert payload == {"market": "DE", "bottles": 600}
    assert fake.completions.last_kwargs is not None
    assert fake.completions.last_kwargs["response_format"] == {"type": "json_object"}


def test_invalid_schema_becomes_typed_error() -> None:
    class Payload(BaseModel):
        bottles: int

    fake = FakeSdkClient(completion(content='{"bottles":"many"}'))
    client = QwenClient(settings=Settings(), sdk_client=fake)

    with pytest.raises(QwenClientError) as captured:
        client.complete_json(
            [{"role": "user", "content": "Return JSON."}],
            schema=Payload,
        )

    assert captured.value.info.code == "QWEN_INVALID_RESPONSE"


def test_tool_call_is_normalized_and_roundtrip_serializable() -> None:
    fake = FakeSdkClient(
        completion(
            content=None,
            finish_reason="tool_calls",
            tool_calls=[tool_call("search_catalog", {"query": "Albariño"})],
        )
    )
    client = QwenClient(settings=Settings(), sdk_client=fake)

    turn = client.request_tools(
        [{"role": "user", "content": "Find Albariño."}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_catalog",
                    "description": "Search the demo catalog.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        tool_choice="required",
    )

    assert turn.tool_calls[0].name == "search_catalog"
    assert turn.tool_calls[0].arguments == {"query": "Albariño"}
    assistant_message = turn.as_assistant_message()
    assert assistant_message["tool_calls"][0]["id"] == "call-1"
