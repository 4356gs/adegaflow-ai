"""Bounded orchestration for inquiry analysis and product recommendation."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agent.registry import RegistryExecutionResult, ToolRegistry
from app.ai.prompts import (
    INQUIRY_ANALYSIS_PROMPT_VERSION,
    PRODUCT_RECOMMENDATION_PROMPT_VERSION,
    load_product_recommendation_prompt,
)
from app.ai.schemas import ModelTurn, ToolCall
from app.db.models import AgentRun, Inquiry
from app.domain.analysis import InquiryAnalysis
from app.domain.enums import AgentRunStatus, AgentRunStep
from app.domain.recommendation import (
    RecommendationContext,
    RecommendationDraft,
    RecommendationEvidence,
    RecommendationValidationOutcome,
    StockEvidence,
)
from app.domain.schemas import ProductRecord
from app.repositories.agent_runs import AgentRunRepository
from app.services.inquiry_analysis import (
    InquiryAnalysisError,
    InquiryAnalysisService,
)
from app.services.recommendation_validation import (
    RecommendationValidationService,
)

Message = dict[str, Any]
ToolDefinition = dict[str, Any]


class RecommendationModelClient(Protocol):
    """Provider-neutral model capabilities required by the orchestrator."""

    def request_tools(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ToolDefinition],
        tool_choice: str | dict[str, Any] = "auto",
        model: str | None = None,
    ) -> ModelTurn: ...

    def complete_json(
        self,
        messages: Sequence[Message],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]: ...


class OrchestrationError(RuntimeError):
    """Safe error raised when orchestration cannot create a run."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Terminal persisted state returned to application callers."""

    run_id: str
    status: AgentRunStatus
    result_payload: dict[str, object]
    error_code: str | None


@dataclass(slots=True)
class _RunBudget:
    model_rounds: int = 0
    tool_executions: int = 0
    correction_used: bool = False


@dataclass(slots=True)
class _EvidenceAccumulator:
    retrieved_product_ids: list[UUID] = field(default_factory=list)
    products: dict[UUID, ProductRecord] = field(default_factory=dict)
    stock_items: dict[UUID, StockEvidence] = field(default_factory=dict)

    def snapshot(self) -> RecommendationEvidence:
        return RecommendationEvidence(
            retrieved_product_ids=list(
                dict.fromkeys(self.retrieved_product_ids)
            ),
            products=list(self.products.values()),
            stock_items=list(self.stock_items.values()),
        )


class _TerminalFailure(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _TerminalReview(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


class BoundedRecommendationOrchestrator:
    """Execute one stateful recommendation run within explicit limits."""

    def __init__(
        self,
        session: Session,
        client: RecommendationModelClient,
        *,
        model: str,
        max_model_rounds: int = 6,
        max_tool_executions: int = 10,
        max_read_retries: int = 1,
    ) -> None:
        if max_model_rounds < 2:
            raise ValueError("max_model_rounds must be at least 2.")
        if max_tool_executions < 1:
            raise ValueError("max_tool_executions must be positive.")
        if max_read_retries not in {0, 1}:
            raise ValueError("max_read_retries must be zero or one.")

        self.session = session
        self.client = client
        self.model = model
        self.max_model_rounds = max_model_rounds
        self.max_tool_executions = max_tool_executions
        self.max_read_retries = max_read_retries
        self.run_repository = AgentRunRepository(session)
        self.registry = ToolRegistry(session, self.run_repository)
        self.validator = RecommendationValidationService()

    def run(self, inquiry_id: UUID | str) -> OrchestrationResult:
        """Run the bounded workflow and persist one terminal state."""

        normalized_id = str(inquiry_id)
        inquiry = self.session.get(Inquiry, normalized_id)
        if inquiry is None:
            raise OrchestrationError(
                code="INQUIRY_NOT_FOUND",
                message="The requested inquiry does not exist.",
            )

        raw_message = inquiry.raw_message
        customer_id = inquiry.customer_id
        run = self.run_repository.create_run(
            inquiry_id=normalized_id,
            model=self.model,
            prompt_versions={
                "inquiry_analysis": INQUIRY_ANALYSIS_PROMPT_VERSION,
                "product_recommendation": (
                    PRODUCT_RECOMMENDATION_PROMPT_VERSION
                ),
            },
        )
        self.run_repository.append_event(
            run=run,
            event_type="run_created",
            step=AgentRunStep.QUEUED,
            payload={
                "max_model_rounds": self.max_model_rounds,
                "max_tool_executions": self.max_tool_executions,
            },
        )
        self.session.commit()

        budget = _RunBudget()
        run_id = run.id

        try:
            analysis, missing_fields = self._resolve_analysis(
                run_id=run_id,
                inquiry_id=normalized_id,
                budget=budget,
            )
            context = self._recommendation_context(analysis)
            memory = self._retrieve_memory(
                run_id=run_id,
                customer_id=customer_id,
                budget=budget,
            )
            messages = self._initial_messages(
                raw_message=raw_message,
                analysis=analysis,
                missing_fields=missing_fields,
                memory=memory,
                context=context,
            )
            evidence = _EvidenceAccumulator()
            selection_complete, unknown_tool_seen = self._selection_loop(
                run_id=run_id,
                messages=messages,
                evidence=evidence,
                budget=budget,
            )
            if not selection_complete:
                raise _TerminalReview(
                    code="RUN_LIMIT_REACHED",
                    message=(
                        "The model-round limit was reached before "
                        "selection completed."
                    ),
                    payload={
                        "model_rounds": budget.model_rounds,
                        "tool_executions": budget.tool_executions,
                    },
                )

            draft = self._request_draft(
                run_id=run_id,
                messages=messages,
                budget=budget,
            )
            outcome = self._validate(
                run_id=run_id,
                draft=draft,
                context=context,
                evidence=evidence.snapshot(),
            )
            if outcome.valid:
                return self._complete(run_id, outcome)

            if unknown_tool_seen:
                return self._needs_review(
                    run_id,
                    code="UNKNOWN_TOOL",
                    message=(
                        "The model requested an unknown tool and did not "
                        "produce a verifiable recommendation."
                    ),
                    payload=self._review_payload(
                        draft=draft,
                        outcome=outcome,
                        budget=budget,
                    ),
                )

            correctable = any(
                issue.correctable for issue in outcome.issues
            )
            if (
                correctable
                and not budget.correction_used
                and budget.model_rounds < self.max_model_rounds
            ):
                corrected = self._request_correction(
                    run_id=run_id,
                    messages=messages,
                    draft=draft,
                    outcome=outcome,
                    evidence=evidence.snapshot(),
                    budget=budget,
                )
                corrected_outcome = self._validate(
                    run_id=run_id,
                    draft=corrected,
                    context=context,
                    evidence=evidence.snapshot(),
                )
                if corrected_outcome.valid:
                    return self._complete(run_id, corrected_outcome)
                draft = corrected
                outcome = corrected_outcome

            error_code = (
                "RUN_LIMIT_REACHED"
                if (
                    correctable
                    and budget.model_rounds >= self.max_model_rounds
                )
                else "RECOMMENDATION_INVALID"
            )
            return self._needs_review(
                run_id,
                code=error_code,
                message=(
                    "The recommendation could not be validated within "
                    "the bounded correction policy."
                ),
                payload=self._review_payload(
                    draft=draft,
                    outcome=outcome,
                    budget=budget,
                ),
            )
        except _TerminalReview as exc:
            return self._needs_review(
                run_id,
                code=exc.code,
                message=exc.message,
                payload=exc.payload,
            )
        except InquiryAnalysisError as exc:
            return self._fail(
                run_id,
                code=exc.code,
                message=exc.message,
            )
        except _TerminalFailure as exc:
            return self._fail(
                run_id,
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:
            provider_error = self._provider_error(exc)
            if provider_error is not None:
                code, message = provider_error
                return self._fail(
                    run_id,
                    code=code,
                    message=message,
                )
            return self._fail(
                run_id,
                code="UNEXPECTED_ERROR",
                message="The recommendation run failed unexpectedly.",
            )

    def _resolve_analysis(
        self,
        *,
        run_id: str,
        inquiry_id: str,
        budget: _RunBudget,
    ) -> tuple[InquiryAnalysis, list[str]]:
        run = self._require_run(run_id)
        self._set_step(
            run,
            AgentRunStep.ANALYZING,
            event_type="analysis_started",
        )
        inquiry = self.session.get(Inquiry, inquiry_id)
        if inquiry is None:
            raise _TerminalFailure(
                code="INQUIRY_NOT_FOUND",
                message="The inquiry was removed during orchestration.",
            )

        if inquiry.extracted_data:
            try:
                analysis = InquiryAnalysis.model_validate(
                    inquiry.extracted_data
                )
            except ValidationError:
                pass
            else:
                self.run_repository.append_event(
                    run=run,
                    event_type="analysis_reused",
                    step=AgentRunStep.ANALYZING,
                    payload={
                        "schema_version": analysis.schema_version,
                    },
                )
                self.session.commit()
                return analysis, list(inquiry.missing_fields)

        if budget.model_rounds >= self.max_model_rounds:
            raise _TerminalReview(
                code="RUN_LIMIT_REACHED",
                message="No model round remained for inquiry analysis.",
            )

        budget.model_rounds += 1
        self.session.commit()
        result = InquiryAnalysisService(
            self.session,
            self.client,
        ).analyze(inquiry_id)

        run = self._require_run(run_id)
        self.run_repository.append_event(
            run=run,
            event_type="analysis_completed",
            step=AgentRunStep.ANALYZING,
            payload={
                "model": result.model,
                "prompt_version": result.prompt_version,
                "missing_field_count": len(result.missing_fields),
            },
        )
        self.session.commit()
        return result.analysis, list(result.missing_fields)

    def _retrieve_memory(
        self,
        *,
        run_id: str,
        customer_id: str | None,
        budget: _RunBudget,
    ) -> dict[str, object]:
        run = self._require_run(run_id)
        self._set_step(
            run,
            AgentRunStep.RETRIEVING_MEMORY,
            event_type="memory_retrieval_started",
        )
        if customer_id is None:
            self.run_repository.append_event(
                run=run,
                event_type="memory_retrieval_skipped",
                step=AgentRunStep.RETRIEVING_MEMORY,
                payload={"reason": "customer_not_linked"},
            )
            self.session.commit()
            return {}

        result = self._execute_tool(
            run_id=run_id,
            tool_name="retrieve_customer_history",
            arguments={
                "customer_id": customer_id,
                "limit": 20,
            },
            budget=budget,
        )
        if not result.success:
            self._raise_for_tool_failure(result)

        data = result.payload.get("data")
        return dict(data) if isinstance(data, dict) else {}

    def _selection_loop(
        self,
        *,
        run_id: str,
        messages: list[Message],
        evidence: _EvidenceAccumulator,
        budget: _RunBudget,
    ) -> tuple[bool, bool]:
        unknown_tool_seen = False
        selection_complete = False

        while budget.model_rounds < self.max_model_rounds - 1:
            run = self._require_run(run_id)
            self._set_step(
                run,
                AgentRunStep.SELECTING_PRODUCTS,
                event_type="selection_round_started",
            )
            self.session.commit()

            turn = self.client.request_tools(
                messages,
                tools=self.registry.selection_definitions(),
                tool_choice="auto",
                model=self.model,
            )
            budget.model_rounds += 1
            messages.append(turn.as_assistant_message())

            run = self._require_run(run_id)
            self._record_model_turn(
                run,
                event_type="selection_round_completed",
                step=AgentRunStep.SELECTING_PRODUCTS,
                turn=turn,
                model_round=budget.model_rounds,
            )
            self.session.commit()

            if not turn.tool_calls:
                selection_complete = True
                break

            for call in turn.tool_calls:
                result = self._execute_tool_call(
                    run_id=run_id,
                    call=call,
                    budget=budget,
                )
                unknown_tool_seen = (
                    unknown_tool_seen
                    or result.error_code == "UNKNOWN_TOOL"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(
                            result.payload,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    }
                )
                if result.success:
                    self._ingest_evidence(
                        tool_name=call.name,
                        payload=result.payload,
                        evidence=evidence,
                    )
                else:
                    self._raise_for_tool_failure(
                        result,
                        allow_model_correction=True,
                    )

        return selection_complete, unknown_tool_seen

    def _request_draft(
        self,
        *,
        run_id: str,
        messages: list[Message],
        budget: _RunBudget,
    ) -> RecommendationDraft:
        if budget.model_rounds >= self.max_model_rounds:
            raise _TerminalReview(
                code="RUN_LIMIT_REACHED",
                message="No model round remained for the recommendation draft.",
            )

        run = self._require_run(run_id)
        self._set_step(
            run,
            AgentRunStep.VALIDATING_RECOMMENDATION,
            event_type="recommendation_draft_requested",
        )
        draft_messages = [
            *messages,
            {
                "role": "user",
                "content": (
                    "Return the recommendation draft now. Use only "
                    "verified product IDs and exact checked quantities."
                ),
            },
        ]
        self.session.commit()

        payload, turn = self.client.complete_json(
            draft_messages,
            schema=RecommendationDraft,
            model=self.model,
            temperature=0.0,
        )
        budget.model_rounds += 1
        draft = RecommendationDraft.model_validate(payload)

        run = self._require_run(run_id)
        self._record_model_turn(
            run,
            event_type="recommendation_draft_received",
            step=AgentRunStep.VALIDATING_RECOMMENDATION,
            turn=turn,
            model_round=budget.model_rounds,
        )
        self.session.commit()
        return draft

    def _request_correction(
        self,
        *,
        run_id: str,
        messages: list[Message],
        draft: RecommendationDraft,
        outcome: RecommendationValidationOutcome,
        evidence: RecommendationEvidence,
        budget: _RunBudget,
    ) -> RecommendationDraft:
        if budget.model_rounds >= self.max_model_rounds:
            raise _TerminalReview(
                code="RUN_LIMIT_REACHED",
                message="No model round remained for correction.",
            )

        budget.correction_used = True
        run = self._require_run(run_id)
        self.run_repository.append_event(
            run=run,
            event_type="recommendation_correction_requested",
            step=AgentRunStep.VALIDATING_RECOMMENDATION,
            payload={
                "issue_codes": [
                    issue.code for issue in outcome.issues
                ],
            },
        )

        correction_messages = [
            *messages,
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": (
                            "Correct the draft once. Return only a new "
                            "recommendation draft."
                        ),
                        "invalid_draft": draft.model_dump(mode="json"),
                        "validation": outcome.correction_payload(),
                        "verified_evidence": evidence.model_dump(
                            mode="json"
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        self.session.commit()

        payload, turn = self.client.complete_json(
            correction_messages,
            schema=RecommendationDraft,
            model=self.model,
            temperature=0.0,
        )
        budget.model_rounds += 1
        corrected = RecommendationDraft.model_validate(payload)

        run = self._require_run(run_id)
        self._record_model_turn(
            run,
            event_type="recommendation_correction_received",
            step=AgentRunStep.VALIDATING_RECOMMENDATION,
            turn=turn,
            model_round=budget.model_rounds,
        )
        self.session.commit()
        return corrected

    def _validate(
        self,
        *,
        run_id: str,
        draft: RecommendationDraft,
        context: RecommendationContext,
        evidence: RecommendationEvidence,
    ) -> RecommendationValidationOutcome:
        run = self._require_run(run_id)
        self._set_step(
            run,
            AgentRunStep.VALIDATING_RECOMMENDATION,
            event_type="recommendation_validation_started",
        )
        outcome = self.validator.validate(
            draft=draft,
            context=context,
            evidence=evidence,
        )
        self.run_repository.append_event(
            run=run,
            event_type=(
                "recommendation_validated"
                if outcome.valid
                else "recommendation_rejected"
            ),
            step=AgentRunStep.VALIDATING_RECOMMENDATION,
            payload={
                "valid": outcome.valid,
                "issue_codes": [
                    issue.code for issue in outcome.issues
                ],
            },
        )
        self.session.commit()
        return outcome

    def _execute_tool_call(
        self,
        *,
        run_id: str,
        call: ToolCall,
        budget: _RunBudget,
    ) -> RegistryExecutionResult:
        return self._execute_tool(
            run_id=run_id,
            tool_name=call.name,
            arguments=call.arguments,
            budget=budget,
        )

    def _execute_tool(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: Mapping[str, Any],
        budget: _RunBudget,
    ) -> RegistryExecutionResult:
        retries = 0
        while True:
            if budget.tool_executions >= self.max_tool_executions:
                raise _TerminalReview(
                    code="RUN_LIMIT_REACHED",
                    message="The tool execution limit was reached.",
                    payload={
                        "model_rounds": budget.model_rounds,
                        "tool_executions": budget.tool_executions,
                    },
                )

            run = self._require_run(run_id)
            step = (
                AgentRunStep.CHECKING_STOCK
                if tool_name == "check_stock"
                else AgentRunStep.RETRIEVING_MEMORY
                if tool_name == "retrieve_customer_history"
                else AgentRunStep.SELECTING_PRODUCTS
            )
            self.run_repository.set_step(run, step)
            result = self.registry.execute(
                run=run,
                tool_name=tool_name,
                arguments=arguments,
            )
            budget.tool_executions += 1
            self.session.commit()

            if (
                result.success
                or not result.retryable
                or retries >= self.max_read_retries
            ):
                return result

            retries += 1
            run = self._require_run(run_id)
            self.run_repository.append_event(
                run=run,
                event_type="tool_retry_scheduled",
                step=step,
                payload={
                    "tool_name": tool_name,
                    "retry_number": retries,
                    "error_code": result.error_code,
                },
            )
            self.session.commit()

    def _ingest_evidence(
        self,
        *,
        tool_name: str,
        payload: Mapping[str, Any],
        evidence: _EvidenceAccumulator,
    ) -> None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return

        try:
            if tool_name == "search_catalog":
                items = data.get("items")
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        product_id = item.get("product_id")
                        if isinstance(product_id, str):
                            evidence.retrieved_product_ids.append(
                                UUID(product_id)
                            )

            elif tool_name == "get_product_details":
                products = data.get("products")
                if isinstance(products, list):
                    for item in products:
                        product = ProductRecord.model_validate(item)
                        product_id = UUID(product.id)
                        evidence.products[product_id] = product

            elif tool_name == "check_stock":
                stock_items = data.get("items")
                if isinstance(stock_items, list):
                    for item in stock_items:
                        stock = StockEvidence.model_validate(item)
                        evidence.stock_items[stock.product_id] = stock
        except (TypeError, ValueError) as exc:
            raise _TerminalFailure(
                code="TOOL_EXECUTION_FAILED",
                message=(
                    "A registered tool returned an invalid evidence "
                    "contract."
                ),
            ) from exc

    def _raise_for_tool_failure(
        self,
        result: RegistryExecutionResult,
        *,
        allow_model_correction: bool = False,
    ) -> None:
        if result.success:
            return
        if result.error_code == "PERSISTENCE_ERROR":
            raise _TerminalFailure(
                code="PERSISTENCE_ERROR",
                message="A required read operation failed.",
            )
        if result.error_code == "TOOL_EXECUTION_FAILED":
            raise _TerminalFailure(
                code="TOOL_EXECUTION_FAILED",
                message="A registered tool could not be executed.",
            )
        if allow_model_correction:
            return
        raise _TerminalReview(
            code=result.error_code or "TOOL_EXECUTION_FAILED",
            message="A required tool did not return usable data.",
        )

    def _complete(
        self,
        run_id: str,
        outcome: RecommendationValidationOutcome,
    ) -> OrchestrationResult:
        if outcome.result is None:
            raise _TerminalFailure(
                code="UNEXPECTED_ERROR",
                message="Validated outcome did not contain a result.",
            )
        run = self._require_run(run_id)
        payload = outcome.result.model_dump(mode="json")
        self.run_repository.complete_run(
            run,
            result_payload=payload,
        )
        self.run_repository.append_event(
            run=run,
            event_type="run_completed",
            step=AgentRunStep.COMPLETED,
            payload={
                "total_bottles": outcome.result.total_bottles,
                "item_count": len(outcome.result.items),
            },
        )
        self.session.commit()
        return self._result(run)

    def _needs_review(
        self,
        run_id: str,
        *,
        code: str,
        message: str,
        payload: Mapping[str, object],
    ) -> OrchestrationResult:
        run = self._require_run(run_id)
        result_payload = {
            "schema_version": "1.0",
            "validation_status": "needs_review",
            **dict(payload),
        }
        self.run_repository.mark_needs_review(
            run,
            result_payload=result_payload,
            error_code=code,
            message_safe=message,
        )
        self.run_repository.append_event(
            run=run,
            event_type="run_needs_review",
            step=AgentRunStep.NEEDS_REVIEW,
            payload={"error_code": code},
        )
        self.session.commit()
        return self._result(run)

    def _fail(
        self,
        run_id: str,
        *,
        code: str,
        message: str,
    ) -> OrchestrationResult:
        self.session.rollback()
        run = self._require_run(run_id)
        self.run_repository.fail_run(
            run,
            error_code=code,
            message_safe=message,
        )
        self.run_repository.append_event(
            run=run,
            event_type="run_failed",
            step=AgentRunStep.FAILED,
            payload={"error_code": code},
        )
        self.session.commit()
        return self._result(run)

    def _set_step(
        self,
        run: AgentRun,
        step: AgentRunStep,
        *,
        event_type: str,
    ) -> None:
        self.run_repository.set_step(run, step)
        self.run_repository.append_event(
            run=run,
            event_type=event_type,
            step=step,
        )

    def _record_model_turn(
        self,
        run: AgentRun,
        *,
        event_type: str,
        step: AgentRunStep,
        turn: ModelTurn,
        model_round: int,
    ) -> None:
        self.run_repository.append_event(
            run=run,
            event_type=event_type,
            step=step,
            payload={
                "model_round": model_round,
                "model": turn.model,
                "finish_reason": turn.finish_reason,
                "tool_call_count": len(turn.tool_calls),
                "prompt_tokens": turn.usage.prompt_tokens,
                "completion_tokens": turn.usage.completion_tokens,
                "total_tokens": turn.usage.total_tokens,
            },
        )

    def _require_run(self, run_id: str) -> AgentRun:
        run = self.run_repository.get_by_id(run_id)
        if run is None:
            raise OrchestrationError(
                code="RUN_NOT_FOUND",
                message="The agent run no longer exists.",
            )
        return run

    @staticmethod
    def _provider_error(exc: Exception) -> tuple[str, str] | None:
        info = getattr(exc, "info", None)
        code = getattr(info, "code", None)
        message = getattr(info, "message", None)
        if isinstance(code, str) and isinstance(message, str):
            return code, message
        return None

    @staticmethod
    def _recommendation_context(
        analysis: InquiryAnalysis,
    ) -> RecommendationContext:
        return RecommendationContext(
            market=analysis.market,
            channel=analysis.channel,
            product_interest=(
                analysis.product_interest[0]
                if analysis.product_interest
                else None
            ),
            estimated_bottles=analysis.estimated_bottles,
            requested_references=None,
            required_certifications=list(
                analysis.certification_requirements
            ),
            budget_total_cents=analysis.budget_total_cents,
            budget_currency=analysis.budget_currency,
        )

    @staticmethod
    def _initial_messages(
        *,
        raw_message: str,
        analysis: InquiryAnalysis,
        missing_fields: list[str],
        memory: Mapping[str, object],
        context: RecommendationContext,
    ) -> list[Message]:
        return [
            {
                "role": "system",
                "content": load_product_recommendation_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "commercial_inquiry": raw_message,
                        "analysis": analysis.model_dump(mode="json"),
                        "missing_fields": missing_fields,
                        "customer_history": dict(memory),
                        "recommendation_context": context.model_dump(
                            mode="json"
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    @staticmethod
    def _review_payload(
        *,
        draft: RecommendationDraft,
        outcome: RecommendationValidationOutcome,
        budget: _RunBudget,
    ) -> dict[str, object]:
        return {
            "draft": draft.model_dump(mode="json"),
            "issues": [
                issue.model_dump(mode="json")
                for issue in outcome.issues
            ],
            "model_rounds": budget.model_rounds,
            "tool_executions": budget.tool_executions,
            "correction_used": budget.correction_used,
        }

    @staticmethod
    def _result(run: AgentRun) -> OrchestrationResult:
        return OrchestrationResult(
            run_id=run.id,
            status=AgentRunStatus(run.status),
            result_payload=dict(run.result_payload),
            error_code=run.error_code,
        )
