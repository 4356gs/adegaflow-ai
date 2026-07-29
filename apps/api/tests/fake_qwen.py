"""Inspectable provider mock used by Block 9 integration tests and demos."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.ai.qwen_client import QwenClientError
from app.ai.schemas import ModelTurn, QwenErrorInfo, ToolCall
from app.domain.artifacts import (
    ALLOWED_EMAIL_NEXT_STEPS,
    ALLOWED_PROPOSAL_NEXT_STEPS,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

PRODUCT_ONE = "11111111-1111-4111-8111-111111111111"
PRODUCT_TWO = "22222222-2222-4222-8222-222222222222"


def _tool_call(call_id: str, name: str, arguments: dict[str, Any]) -> ToolCall:
    return ToolCall(
        id=call_id,
        name=name,
        arguments=arguments,
        raw_arguments=json.dumps(arguments),
    )


def happy_tool_turns() -> list[ModelTurn]:
    return [
        ModelTurn(
            model="fake-qwen",
            finish_reason="tool_calls",
            tool_calls=[
                _tool_call(
                    "call-search",
                    "search_catalog",
                    {
                        "query": "Albariño",
                        "market": "DE",
                        "channel": "specialty_retail",
                        "limit": 10,
                    },
                )
            ],
        ),
        ModelTurn(
            model="fake-qwen",
            finish_reason="tool_calls",
            tool_calls=[
                _tool_call(
                    "call-details",
                    "get_product_details",
                    {"product_ids": [PRODUCT_ONE, PRODUCT_TWO]},
                )
            ],
        ),
        ModelTurn(
            model="fake-qwen",
            finish_reason="tool_calls",
            tool_calls=[
                _tool_call(
                    "call-stock",
                    "check_stock",
                    {
                        "items": [
                            {"product_id": PRODUCT_ONE, "requested_bottles": 300},
                            {"product_id": PRODUCT_TWO, "requested_bottles": 300},
                        ]
                    },
                )
            ],
        ),
        ModelTurn(
            model="fake-qwen",
            content="Evidence collection is complete.",
            finish_reason="stop",
        ),
    ]


def happy_json_payloads() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "1.0",
            "language": "en",
            "intent": "b2b_purchase_inquiry",
            "market": "DE",
            "product_interest": ["Albariño"],
            "estimated_bottles": 600,
            "channel": "specialty_retail",
            "target_horizon_days": 60,
            "samples_requested": False,
            "price_list_requested": False,
            "company_name": "Rhein Selection GmbH",
            "contact_name": "Anna Keller",
        },
        {
            "schema_version": "1.0",
            "items": [
                {
                    "product_id": PRODUCT_ONE,
                    "quantity_bottles": 300,
                    "rationale": "Fresh Albariño suited to specialised German retail.",
                },
                {
                    "product_id": PRODUCT_TWO,
                    "quantity_bottles": 300,
                    "rationale": "A complex second reference for the same channel.",
                },
            ],
            "summary": "Two complementary Albariño references.",
            "warnings": [],
        },
        {
            "schema_version": "1.0",
            "headline": "Galician wines for specialised retail",
            "executive_summary": "A focused selection for human review.",
            "product_positioning": [
                {"product_id": PRODUCT_ONE, "positioning": "Fresh Atlantic style."},
                {"product_id": PRODUCT_TWO, "positioning": "Complex Atlantic style."},
            ],
            "next_steps": [ALLOWED_PROPOSAL_NEXT_STEPS[0]],
            "open_questions": [],
            "warnings": ["Human review is required."],
        },
        {
            "schema_version": "1.0",
            "subject": "Draft proposal for review",
            "introduction": "Thank you for your inquiry.",
            "recommendation_summary": "We prepared a focused selection.",
            "next_step": ALLOWED_EMAIL_NEXT_STEPS[0],
            "questions": [],
            "closing": "Kind regards",
            "warnings": ["Human review is required before sending."],
        },
    ]


def timeout_error() -> QwenClientError:
    return QwenClientError(
        QwenErrorInfo(
            code="QWEN_TIMEOUT",
            message="Qwen Cloud did not respond before the timeout.",
            retryable=True,
            category="timeout",
        )
    )


class FakeQwenClient:
    """Provider-neutral scripted client; all other components remain real."""

    def __init__(
        self,
        session: Session,
        *,
        fail_first_json: bool = False,
    ) -> None:
        self.session = session
        self.tool_turns = happy_tool_turns()
        self.json_payloads = happy_json_payloads()
        self.fail_first_json = fail_first_json
        self.calls: list[str] = []
        self.request_messages: list[list[dict[str, Any]]] = []

    def request_tools(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        tools: Sequence[dict[str, Any]],
        tool_choice: str | dict[str, Any] = "auto",
        model: str | None = None,
    ) -> ModelTurn:
        assert not self.session.in_transaction()
        assert tools
        assert tool_choice == "auto"
        self.calls.append("request_tools")
        self.request_messages.append(list(messages))
        if not self.tool_turns:
            raise AssertionError("No fake tool turn remained.")
        return self.tool_turns.pop(0)

    def complete_json(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]:
        assert not self.session.in_transaction()
        self.calls.append(f"complete_json:{schema.__name__ if schema else 'none'}")
        if self.fail_first_json:
            self.fail_first_json = False
            raise timeout_error()
        if not self.json_payloads:
            raise AssertionError("No fake JSON payload remained.")
        payload = self.json_payloads.pop(0)
        if schema is not None:
            payload = schema.model_validate(payload).model_dump(mode="json")
        return payload, ModelTurn(
            model=model or "fake-qwen",
            content=json.dumps(payload),
            finish_reason="stop",
        )
