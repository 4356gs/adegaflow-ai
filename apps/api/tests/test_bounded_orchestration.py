from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.agent.orchestrator import (
    BoundedRecommendationOrchestrator,
)
from app.ai.qwen_client import QwenClientError
from app.ai.schemas import ModelTurn, QwenErrorInfo, ToolCall
from app.db.models import AgentRun, GeneratedArtifact, Inquiry, Opportunity, Quote
from app.domain.analysis import (
    InquiryAnalysis,
    InquiryIntent,
    compute_missing_fields,
)
from app.domain.artifacts import (
    ALLOWED_EMAIL_NEXT_STEPS,
    ALLOWED_PROPOSAL_NEXT_STEPS,
    EmailDraftNarrative,
    ProposalNarrative,
)
from app.domain.enums import AgentRunStatus, ArtifactType
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.quote_artifacts import GeneratedArtifactRepository
from app.services.artifact_persistence import (
    ArtifactPersistenceError,
    ArtifactPersistenceService,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

INQUIRY_ID = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1"
CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
PRODUCT_ONE = "11111111-1111-4111-8111-111111111111"
PRODUCT_TWO = "22222222-2222-4222-8222-222222222222"


class FakeProviderError(RuntimeError):
    def __init__(self, info: QwenErrorInfo) -> None:
        super().__init__(info.message)
        self.info = info


class FakeModelClient:
    def __init__(
        self,
        session: Session,
        *,
        tool_turns: list[ModelTurn],
        json_payloads: list[dict[str, Any]],
        request_error: Exception | None = None,
        json_errors: dict[int, Exception] | None = None,
    ) -> None:
        self.session = session
        self.tool_turns = list(tool_turns)
        self.json_payloads = list(json_payloads)
        self.request_error = request_error
        self.json_errors = dict(json_errors or {})
        self.request_calls = 0
        self.json_calls = 0

    def request_tools(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        tools: Sequence[dict[str, Any]],
        tool_choice: str | dict[str, Any] = "auto",
        model: str | None = None,
    ) -> ModelTurn:
        assert not self.session.in_transaction()
        assert messages
        assert tools
        assert tool_choice == "auto"
        assert model == "fake-qwen"
        self.request_calls += 1
        if self.request_error is not None:
            raise self.request_error
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
        assert messages
        self.json_calls += 1
        error = self.json_errors.get(self.json_calls)
        if error is not None:
            raise error
        if schema in {ProposalNarrative, EmailDraftNarrative}:
            assert temperature == 0.2
        else:
            assert temperature == 0.0
        if not self.json_payloads:
            raise AssertionError("No fake JSON payload remained.")
        payload = self.json_payloads.pop(0)
        if schema is not None:
            validated = schema.model_validate(payload)
            payload = validated.model_dump(mode="json")
        return payload, ModelTurn(
            model=model or "fake-qwen",
            content=json.dumps(payload),
            finish_reason="stop",
        )


def _analysis() -> InquiryAnalysis:
    return InquiryAnalysis(
        language="en",
        intent=InquiryIntent.B2B_PURCHASE_INQUIRY,
        market="DE",
        product_interest=["Albariño"],
        estimated_bottles=600,
        channel="specialty_retail",
        target_horizon_days=60,
        samples_requested=True,
        price_list_requested=True,
        company_name="Rhein Selection GmbH",
        contact_name="Anna Keller",
    )


def _prepare_inquiry(
    db_session: Session,
    *,
    reuse_analysis: bool = True,
    customer_id: str | None = CUSTOMER_ID,
) -> Inquiry:
    inquiry = db_session.get(Inquiry, INQUIRY_ID)
    assert inquiry is not None
    inquiry.customer_id = customer_id
    inquiry.raw_message = (
        "We need 600 bottles of Albariño for specialised wine shops "
        "in Germany. Recommend two references and send samples."
    )
    if reuse_analysis:
        analysis = _analysis()
        inquiry.extracted_data = analysis.model_dump(mode="json")
        inquiry.missing_fields = compute_missing_fields(analysis)
    else:
        inquiry.extracted_data = {}
        inquiry.missing_fields = []
    db_session.commit()
    return inquiry


def _tool_call(
    call_id: str,
    name: str,
    arguments: dict[str, Any],
) -> ToolCall:
    return ToolCall(
        id=call_id,
        name=name,
        arguments=arguments,
        raw_arguments=json.dumps(arguments),
    )


def _primary_tool_turns() -> list[ModelTurn]:
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
                    {
                        "product_ids": [
                            PRODUCT_ONE,
                            PRODUCT_TWO,
                        ]
                    },
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
                            {
                                "product_id": PRODUCT_ONE,
                                "requested_bottles": 300,
                            },
                            {
                                "product_id": PRODUCT_TWO,
                                "requested_bottles": 300,
                            },
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


def _valid_draft() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "items": [
            {
                "product_id": PRODUCT_ONE,
                "quantity_bottles": 300,
                "rationale": (
                    "Fresh Albariño suited to specialised German retail."
                ),
            },
            {
                "product_id": PRODUCT_TWO,
                "quantity_bottles": 300,
                "rationale": (
                    "A more complex second reference for the same channel."
                ),
            },
        ],
        "summary": "Two complementary Albariño references.",
        "warnings": [],
    }


def _valid_proposal() -> dict[str, Any]:
    return {
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
    }


def _valid_email() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "subject": "Draft proposal for review",
        "introduction": "Thank you for your inquiry.",
        "recommendation_summary": "We prepared a focused selection.",
        "next_step": ALLOWED_EMAIL_NEXT_STEPS[0],
        "questions": [],
        "closing": "Kind regards",
        "warnings": ["Human review is required before sending."],
    }


def _successful_json_payloads() -> list[dict[str, Any]]:
    return [_valid_draft(), _valid_proposal(), _valid_email()]


def _run_for_inquiry(
    db_session: Session,
    client: FakeModelClient,
    **limits: int,
):
    orchestrator = BoundedRecommendationOrchestrator(
        db_session,
        client,
        model="fake-qwen",
        **limits,
    )
    return orchestrator.run(INQUIRY_ID)


def test_completes_primary_scenario_with_trace_and_no_writes(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    before_opportunities = db_session.scalar(
        select(func.count()).select_from(Opportunity)
    )
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=_successful_json_payloads(),
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "HUMAN_REVIEW_REQUIRED"
    recommendation = result.result_payload["recommendation"]
    assert isinstance(recommendation, dict)
    assert recommendation["total_bottles"] == 600
    quote = result.result_payload["quote"]
    assert isinstance(quote, dict)
    assert quote["subtotal_cents"] == 609000
    artifacts = result.result_payload["artifacts"]
    assert isinstance(artifacts, list)
    assert [item["artifact_type"] for item in artifacts] == [
        "proposal",
        "email_draft",
    ]
    assert all("content" not in item for item in artifacts)

    after_opportunities = db_session.scalar(
        select(func.count()).select_from(Opportunity)
    )
    assert after_opportunities == before_opportunities

    repository = AgentRunRepository(db_session)
    executions = repository.list_tool_executions(result.run_id)
    assert [execution.tool_name for execution in executions] == [
        "retrieve_customer_history",
        "search_catalog",
        "get_product_details",
        "check_stock",
    ]

    events = repository.list_events(result.run_id)
    event_types = [event.event_type for event in events]
    assert "analysis_reused" in event_types
    assert "recommendation_validated" in event_types
    assert event_types[-10:] == [
        "quote_calculation_started",
        "quote_calculated",
        "quote_persisted",
        "proposal_generation_started",
        "proposal_received",
        "proposal_persisted",
        "email_generation_started",
        "email_draft_received",
        "email_draft_persisted",
        "run_needs_review",
    ]
    assert client.request_calls == 4
    assert client.json_calls == 3


def test_runs_analysis_when_persisted_analysis_is_missing(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session, reuse_analysis=False)
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[
            _analysis().model_dump(mode="json"),
            _valid_draft(),
            _valid_proposal(),
            _valid_email(),
        ],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    inquiry = db_session.get(Inquiry, INQUIRY_ID)
    assert inquiry is not None
    assert inquiry.extracted_data["estimated_bottles"] == 600

    events = AgentRunRepository(db_session).list_events(result.run_id)
    assert "analysis_completed" in {
        event.event_type for event in events
    }
    assert client.json_calls == 4


def test_skips_memory_when_inquiry_has_no_customer(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session, customer_id=None)
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=_successful_json_payloads(),
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    repository = AgentRunRepository(db_session)
    executions = repository.list_tool_executions(result.run_id)
    assert "retrieve_customer_history" not in {
        execution.tool_name for execution in executions
    }
    events = repository.list_events(result.run_id)
    assert "memory_retrieval_skipped" in {
        event.event_type for event in events
    }


def test_allows_exactly_one_controlled_correction(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    invalid = _valid_draft()
    invalid["items"][0]["quantity_bottles"] = 294
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[
            invalid,
            _valid_draft(),
            _valid_proposal(),
            _valid_email(),
        ],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert client.json_calls == 4
    events = AgentRunRepository(db_session).list_events(result.run_id)
    event_types = [event.event_type for event in events]
    assert event_types.count(
        "recommendation_correction_requested"
    ) == 1
    assert event_types.count(
        "recommendation_correction_received"
    ) == 1


def test_provider_timeout_fails_with_safe_error(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    client = FakeModelClient(
        db_session,
        tool_turns=[],
        json_payloads=[],
        request_error=FakeProviderError(
            QwenErrorInfo(
                code="QWEN_TIMEOUT",
                message="Provider timed out.",
                retryable=True,
                category="timeout",
            )
        ),
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.FAILED
    assert result.error_code == "QWEN_TIMEOUT"
    run = db_session.get(AgentRun, result.run_id)
    assert run is not None
    assert run.error_message_safe == "Provider timed out."


def test_model_round_limit_finishes_needs_review(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    repeated = ModelTurn(
        model="fake-qwen",
        finish_reason="tool_calls",
        tool_calls=[
            _tool_call(
                "repeat-search",
                "search_catalog",
                {
                    "query": "Albariño",
                    "market": "DE",
                    "channel": "specialty_retail",
                    "limit": 5,
                },
            )
        ],
    )
    client = FakeModelClient(
        db_session,
        tool_turns=[repeated, repeated.model_copy(deep=True)],
        json_payloads=[],
    )

    result = _run_for_inquiry(
        db_session,
        client,
        max_model_rounds=3,
    )

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "RUN_LIMIT_REACHED"
    assert client.request_calls == 2
    assert client.json_calls == 0


def test_tool_limit_finishes_needs_review(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    client = FakeModelClient(
        db_session,
        tool_turns=[
            ModelTurn(
                model="fake-qwen",
                finish_reason="tool_calls",
                tool_calls=[
                    _tool_call(
                        "search-one",
                        "search_catalog",
                        {"query": "Albariño"},
                    ),
                    _tool_call(
                        "search-two",
                        "search_catalog",
                        {"query": "Albariño"},
                    ),
                ],
            )
        ],
        json_payloads=[],
    )

    result = _run_for_inquiry(
        db_session,
        client,
        max_tool_executions=2,
    )

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "RUN_LIMIT_REACHED"
    executions = AgentRunRepository(
        db_session
    ).list_tool_executions(result.run_id)
    assert len(executions) == 2


def test_unknown_tool_never_executes_and_finishes_needs_review(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    client = FakeModelClient(
        db_session,
        tool_turns=[
            ModelTurn(
                model="fake-qwen",
                finish_reason="tool_calls",
                tool_calls=[
                    _tool_call(
                        "unknown",
                        "reserve_inventory",
                        {"product_id": PRODUCT_ONE},
                    )
                ],
            ),
            ModelTurn(
                model="fake-qwen",
                content="No more tools.",
                finish_reason="stop",
            ),
        ],
        json_payloads=[_valid_draft()],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "UNKNOWN_TOOL"
    executions = AgentRunRepository(
        db_session
    ).list_tool_executions(result.run_id)
    unknown = [
        execution
        for execution in executions
        if execution.tool_name == "reserve_inventory"
    ]
    assert len(unknown) == 1
    assert unknown[0].status == "rejected"


def test_invalid_proposal_preserves_quote_as_partial_result(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[_valid_draft(), {"invalid": True}],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "PROPOSAL_INVALID_RESPONSE"
    assert "quote" in result.result_payload
    assert result.result_payload["artifacts"] == []
    events = AgentRunRepository(db_session).list_events(result.run_id)
    assert [event.event_type for event in events][-3:] == [
        "proposal_rejected",
        "artifact_generation_partial",
        "run_needs_review",
    ]


def test_qwen_invalid_email_preserves_confirmed_proposal(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    error = QwenClientError(
        QwenErrorInfo(
            code="QWEN_INVALID_RESPONSE",
            message="JSON output does not conform after repair.",
            retryable=True,
            category="invalid_response",
        )
    )
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[_valid_draft(), _valid_proposal()],
        json_errors={3: error},
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "QWEN_INVALID_RESPONSE"
    artifacts = result.result_payload["artifacts"]
    assert isinstance(artifacts, list)
    assert [item["artifact_type"] for item in artifacts] == ["proposal"]
    persisted = GeneratedArtifactRepository(db_session).list_by_run(result.run_id)
    assert [item.artifact_type for item in persisted] == ["proposal"]
    events = AgentRunRepository(db_session).list_events(result.run_id)
    assert [event.event_type for event in events][-3:] == [
        "email_draft_rejected",
        "artifact_generation_partial",
        "run_needs_review",
    ]


def test_unauthorized_email_next_step_finishes_partial_review(
    db_session: Session,
) -> None:
    _prepare_inquiry(db_session)
    unauthorized_email = {
        **_valid_email(),
        "next_step": "Send the email automatically.",
    }
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[
            _valid_draft(),
            _valid_proposal(),
            unauthorized_email,
        ],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.NEEDS_REVIEW
    assert result.error_code == "EMAIL_NEXT_STEP_NOT_ALLOWED"
    assert result.result_payload["quote"]
    artifacts = result.result_payload["artifacts"]
    assert isinstance(artifacts, list)
    assert [item["artifact_type"] for item in artifacts] == ["proposal"]
    persisted = GeneratedArtifactRepository(db_session).list_by_run(result.run_id)
    assert [item.artifact_type for item in persisted] == ["proposal"]
    events = AgentRunRepository(db_session).list_events(result.run_id)
    assert [event.event_type for event in events][-2:] == [
        "artifact_generation_partial",
        "run_needs_review",
    ]


def test_email_persistence_failure_rolls_back_only_email(
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _prepare_inquiry(db_session)

    def fail_email_persistence(
        service: ArtifactPersistenceService,
        *,
        agent_run_id: str,
        quote_id: str,
        proposal_artifact_id: str,
        narrative: EmailDraftNarrative,
    ) -> Any:
        del narrative
        service.session.add(
            GeneratedArtifact(
                id="99999999-9999-4999-8999-999999999998",
                agent_run_id=agent_run_id,
                quote_id=quote_id,
                artifact_type=ArtifactType.EMAIL_DRAFT.value,
                language="en",
                schema_version="1.0",
                content={"transient": True},
                review_status="needs_review",
            )
        )
        service.session.flush()
        raise ArtifactPersistenceError(
            code="QUOTE_INTEGRITY_ERROR",
            message="The email draft could not be persisted.",
        )

    monkeypatch.setattr(
        ArtifactPersistenceService,
        "persist_email_draft",
        fail_email_persistence,
    )
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=_successful_json_payloads(),
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.FAILED
    assert result.error_code == "QUOTE_INTEGRITY_ERROR"
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Quote)) == 1
    persisted = GeneratedArtifactRepository(db_session).list_by_run(result.run_id)
    assert [item.artifact_type for item in persisted] == ["proposal"]
    artifacts = result.result_payload["artifacts"]
    assert isinstance(artifacts, list)
    assert [item["artifact_type"] for item in artifacts] == ["proposal"]
    events = AgentRunRepository(db_session).list_events(result.run_id)
    assert [event.event_type for event in events][-2:] == [
        "artifact_generation_partial",
        "run_failed",
    ]


def test_proposal_persistence_failure_preserves_quote(
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _prepare_inquiry(db_session)

    def fail_proposal_persistence(
        service: ArtifactPersistenceService,
        *,
        agent_run_id: str,
        quote_id: str,
        narrative: ProposalNarrative,
    ) -> Any:
        del narrative
        service.session.add(
            GeneratedArtifact(
                id="99999999-9999-4999-8999-999999999997",
                agent_run_id=agent_run_id,
                quote_id=quote_id,
                artifact_type=ArtifactType.PROPOSAL.value,
                language="en",
                schema_version="1.0",
                content={"transient": True},
                review_status="needs_review",
            )
        )
        service.session.flush()
        raise ArtifactPersistenceError(
            code="QUOTE_INTEGRITY_ERROR",
            message="The proposal could not be persisted.",
        )

    monkeypatch.setattr(
        ArtifactPersistenceService,
        "persist_proposal",
        fail_proposal_persistence,
    )
    client = FakeModelClient(
        db_session,
        tool_turns=_primary_tool_turns(),
        json_payloads=[_valid_draft(), _valid_proposal()],
    )

    result = _run_for_inquiry(db_session, client)

    assert result.status is AgentRunStatus.FAILED
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Quote)) == 1
    assert GeneratedArtifactRepository(db_session).list_by_run(result.run_id) == []
    assert result.result_payload["artifacts"] == []
    event_types = [
        event.event_type
        for event in AgentRunRepository(db_session).list_events(result.run_id)
    ]
    assert "proposal_received" in event_types
    assert event_types[-2:] == ["artifact_generation_partial", "run_failed"]
