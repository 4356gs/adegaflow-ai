"""Atomic, idempotent internal actions executed after artifact generation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    Customer,
    CustomerMemory,
    FollowUpTask,
    GeneratedArtifact,
    Inquiry,
    Opportunity,
    Quote,
    ToolExecution,
)
from app.domain.analysis import InquiryAnalysis
from app.domain.enums import (
    AgentRunStep,
    ArtifactType,
    FollowUpStatus,
    InternalActionName,
    ReviewStatus,
    ToolExecutionStatus,
)
from app.domain.internal_actions import (
    CustomerActionReference,
    FollowUpActionInput,
    FollowUpActionReference,
    InternalActionEnvelope,
    InternalActionsResult,
    MemoryActionInput,
    MemoryActionReference,
    OpportunityActionInput,
    OpportunityActionReference,
    canonical_fingerprint,
)
from app.domain.recommendation import ValidatedRecommendation
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.internal_actions import InternalActionRepository
from app.repositories.quote_artifacts import GeneratedArtifactRepository, QuoteRepository
from app.services.opportunity_qualification import (
    MemoryExtractionService,
    OpportunityQualificationService,
)


class InternalActionError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        action_name: InternalActionName | None = None,
        fingerprint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action_name = action_name
        self.fingerprint = fingerprint


class InternalActionsService:
    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.clock = clock or (lambda: datetime.now(UTC))
        self.runs = AgentRunRepository(session)
        self.actions = InternalActionRepository(session)

    def execute(self, run_id: str) -> InternalActionsResult:
        try:
            run, inquiry, analysis, recommendation = self._load_context(run_id)
            customer, customer_created = self._resolve_customer(run, inquiry, analysis)
            opportunity_input = OpportunityQualificationService().build(
                run_id=run.id,
                inquiry=inquiry,
                customer_id=customer.id,
                analysis=analysis,
                recommendation=recommendation,
            )
            opportunity_envelope = self._opportunity(run, opportunity_input)
            opportunity_id = str(opportunity_envelope.result["opportunity_id"])
            followup_input = FollowUpActionInput(
                opportunity_id=UUID(opportunity_id),
                title=(
                    "Follow up on proposal, pricing and samples"
                    if analysis.samples_requested
                    else "Follow up on proposal and pricing"
                ),
                due_at=self._utc_now() + timedelta(days=7),
                status=FollowUpStatus.PENDING,
                idempotency_key=f"{run.id}:create_followup_task",
            )
            followup_envelope = self._followup(run, followup_input)
            memory_input = MemoryActionInput(
                customer_id=UUID(customer.id),
                source_inquiry_id=UUID(inquiry.id),
                memories=MemoryExtractionService().build(analysis),
                idempotency_key=f"{run.id}:save_customer_memory",
            )
            memory_envelope = self._memory(run, memory_input)

            result = InternalActionsResult(
                customer=CustomerActionReference(
                    customer_id=UUID(customer.id), created=customer_created
                ),
                opportunity=OpportunityActionReference.model_validate(opportunity_envelope.result),
                followup=FollowUpActionReference.model_validate(followup_envelope.result),
                memory=MemoryActionReference.model_validate(memory_envelope.result),
            )
            run.result_payload = {
                "schema_version": "1.0",
                "validation_status": "needs_review",
                **dict(run.result_payload),
                **result.model_dump(mode="json"),
            }
            self.runs.append_event(
                run=run,
                event_type="internal_actions_completed",
                step=AgentRunStep.PERSISTING_ACTIONS,
                payload={
                    "customer_created": customer_created,
                    "memory_count": result.memory.saved_count,
                },
            )
            self.runs.mark_needs_review(
                run,
                result_payload=run.result_payload,
                error_code="HUMAN_REVIEW_REQUIRED",
                message_safe=("The generated commercial artifacts require human review."),
            )
            self.runs.append_event(
                run=run,
                event_type="run_needs_review",
                step=AgentRunStep.NEEDS_REVIEW,
                payload={"error_code": "HUMAN_REVIEW_REQUIRED"},
            )
            return result
        except InternalActionError:
            raise
        except SQLAlchemyError as exc:
            raise InternalActionError(
                code="INTERNAL_ACTION_PERSISTENCE_ERROR",
                message="The internal actions could not be persisted.",
            ) from exc
        except (LookupError, ValueError, ValidationError) as exc:
            raise InternalActionError(
                code="INTERNAL_ACTION_VALIDATION_FAILED",
                message="Internal action inputs could not be validated.",
            ) from exc

    def _load_context(
        self, run_id: str
    ) -> tuple[AgentRun, Inquiry, InquiryAnalysis, ValidatedRecommendation]:
        run = self.runs.get_by_id(run_id)
        if run is None:
            raise LookupError("Agent run does not exist.")
        inquiry = self.session.get(Inquiry, run.inquiry_id)
        if inquiry is None:
            raise LookupError("Inquiry does not exist.")
        analysis = InquiryAnalysis.model_validate(inquiry.extracted_data)
        recommendation_payload = run.result_payload.get("recommendation")
        recommendation = ValidatedRecommendation.model_validate(recommendation_payload)
        quote = QuoteRepository(self.session).get_by_run_id(run.id)
        if quote is None or quote.status != "draft" or quote.currency != "EUR":
            raise LookupError("A valid draft quote is required.")
        artifacts = GeneratedArtifactRepository(self.session).list_by_run(run.id)
        self._validate_artifacts(run, quote, artifacts)
        return run, inquiry, analysis, recommendation

    @staticmethod
    def _validate_artifacts(
        run: AgentRun, quote: Quote, artifacts: list[GeneratedArtifact]
    ) -> None:
        by_type = {item.artifact_type: item for item in artifacts}
        if set(by_type) != {ArtifactType.PROPOSAL.value, ArtifactType.EMAIL_DRAFT.value}:
            raise LookupError("Both generated artifacts are required.")
        if any(
            item.agent_run_id != run.id
            or item.quote_id != quote.id
            or item.review_status != ReviewStatus.NEEDS_REVIEW.value
            for item in artifacts
        ):
            raise ValueError("Generated artifacts do not satisfy the action boundary.")

    def _resolve_customer(
        self, run: AgentRun, inquiry: Inquiry, analysis: InquiryAnalysis
    ) -> tuple[Customer, bool]:
        self.runs.append_event(
            run=run,
            event_type="customer_resolution_started",
            step=AgentRunStep.PERSISTING_ACTIONS,
        )
        if inquiry.customer_id is not None:
            customer = self.session.get(Customer, inquiry.customer_id)
            if customer is None:
                raise LookupError("Associated customer does not exist.")
            self.runs.append_event(
                run=run,
                event_type="customer_reused",
                step=AgentRunStep.PERSISTING_ACTIONS,
                payload={"customer_id": customer.id},
            )
            return customer, False
        if not analysis.company_name or not analysis.market:
            raise ValueError("Company name and market are required for a new customer.")
        language = analysis.language if len(analysis.language) == 2 else "en"
        customer = Customer(
            id=str(uuid4()),
            company_name=analysis.company_name,
            country_code=analysis.market,
            contact_name=analysis.contact_name,
            email=analysis.contact_email,
            preferred_language=language,
        )
        self.session.add(customer)
        inquiry.customer_id = customer.id
        self.session.flush()
        self.runs.append_event(
            run=run,
            event_type="customer_created",
            step=AgentRunStep.PERSISTING_ACTIONS,
            payload={"customer_id": customer.id, "market": customer.country_code},
        )
        return customer, True

    def _opportunity(self, run: AgentRun, payload: object) -> InternalActionEnvelope:
        validated = OpportunityActionInput.model_validate(payload)
        action = InternalActionName.CREATE_CRM_OPPORTUNITY
        fingerprint = canonical_fingerprint(validated)
        execution, started = self._start_action(run, action, validated.idempotency_key, fingerprint)
        reused = self._reuse(run, action, validated.idempotency_key, fingerprint)
        if reused is not None:
            opportunity_id = str(reused.get("opportunity_id", ""))
            opportunity = self.session.get(Opportunity, opportunity_id)
            if (
                opportunity is None
                or opportunity.inquiry_id != str(validated.inquiry_id)
                or opportunity.customer_id != str(validated.customer_id)
            ):
                self._conflict(action, fingerprint, "Opportunity receipt is inconsistent.")
            self._finish_action(run, execution, action, reused, started, True)
            return InternalActionEnvelope(
                action_name=action, reused=True, fingerprint=fingerprint, result=reused
            )
        if self.actions.get_opportunity_for_inquiry(str(validated.inquiry_id)) is not None:
            self._conflict(action, fingerprint, "Opportunity exists without an equivalent receipt.")
        opportunity = self.actions.add_opportunity(
            inquiry_id=str(validated.inquiry_id),
            customer_id=str(validated.customer_id),
            title=validated.title,
            stage=str(validated.stage),
            priority=validated.priority.value,
            score=validated.score,
            market=validated.market,
            channel=validated.channel,
            estimated_bottles=validated.estimated_bottles,
            target_date=validated.target_date,
            summary=validated.summary,
        )
        result: dict[str, object] = {
            "opportunity_id": opportunity.id,
            "stage": opportunity.stage,
            "priority": opportunity.priority,
            "score": opportunity.score,
        }
        self.actions.add_receipt(
            agent_run_id=run.id,
            action_name=action,
            idempotency_key=validated.idempotency_key,
            fingerprint=fingerprint,
            result_payload=result,
        )
        self._finish_action(run, execution, action, result, started, False)
        return InternalActionEnvelope(
            action_name=action, reused=False, fingerprint=fingerprint, result=result
        )

    def _followup(self, run: AgentRun, validated: FollowUpActionInput) -> InternalActionEnvelope:
        action = InternalActionName.CREATE_FOLLOWUP_TASK
        fingerprint = canonical_fingerprint(validated)
        execution, started = self._start_action(run, action, validated.idempotency_key, fingerprint)
        reused = self._reuse(run, action, validated.idempotency_key, fingerprint)
        if reused is not None:
            followup_id = str(reused.get("followup_task_id", ""))
            if self.session.get(FollowUpTask, followup_id) is None:
                self._conflict(action, fingerprint, "Follow-up receipt is inconsistent.")
            self._finish_action(run, execution, action, reused, started, True)
            return InternalActionEnvelope(
                action_name=action, reused=True, fingerprint=fingerprint, result=reused
            )
        if self.session.get(Opportunity, str(validated.opportunity_id)) is None:
            raise LookupError("Opportunity does not exist.")
        followup = self.actions.add_followup(
            opportunity_id=str(validated.opportunity_id),
            title=validated.title,
            due_at=validated.due_at,
            status=str(validated.status),
        )
        result: dict[str, object] = {
            "followup_task_id": followup.id,
            "due_at": validated.due_at.isoformat(),
            "status": followup.status,
        }
        self.actions.add_receipt(
            agent_run_id=run.id,
            action_name=action,
            idempotency_key=validated.idempotency_key,
            fingerprint=fingerprint,
            result_payload=result,
        )
        self._finish_action(run, execution, action, result, started, False)
        return InternalActionEnvelope(
            action_name=action, reused=False, fingerprint=fingerprint, result=result
        )

    def _memory(self, run: AgentRun, validated: MemoryActionInput) -> InternalActionEnvelope:
        action = InternalActionName.SAVE_CUSTOMER_MEMORY
        fingerprint = canonical_fingerprint(validated)
        execution, started = self._start_action(run, action, validated.idempotency_key, fingerprint)
        reused = self._reuse(run, action, validated.idempotency_key, fingerprint)
        if reused is not None:
            receipt_memory_ids = reused.get("memory_ids")
            if not isinstance(receipt_memory_ids, list) or any(
                not isinstance(memory_id, str)
                or (memory := self.session.get(CustomerMemory, memory_id)) is None
                or memory.customer_id != str(validated.customer_id)
                or memory.source_inquiry_id != str(validated.source_inquiry_id)
                for memory_id in receipt_memory_ids
            ):
                self._conflict(action, fingerprint, "Memory receipt is inconsistent.")
            self._finish_action(run, execution, action, reused, started, True)
            return InternalActionEnvelope(
                action_name=action, reused=True, fingerprint=fingerprint, result=reused
            )
        memory_ids: list[str] = []
        for fact in validated.memories:
            category = str(fact.category)
            existing = self.actions.find_memory(
                customer_id=str(validated.customer_id),
                category=category,
                normalized_content=fact.content,
                source_inquiry_id=str(validated.source_inquiry_id),
            )
            memory = existing or self.actions.add_memory(
                customer_id=str(validated.customer_id),
                category=category,
                content=fact.content,
                confidence=1.0,
                source_inquiry_id=str(validated.source_inquiry_id),
                is_active=True,
            )
            memory_ids.append(memory.id)
        result: dict[str, object] = {
            "saved_count": len(memory_ids),
            "memory_ids": memory_ids,
            "warning": None if memory_ids else "No permitted explicit memory facts were found.",
        }
        self.actions.add_receipt(
            agent_run_id=run.id,
            action_name=action,
            idempotency_key=validated.idempotency_key,
            fingerprint=fingerprint,
            result_payload=result,
        )
        self._finish_action(run, execution, action, result, started, False)
        return InternalActionEnvelope(
            action_name=action, reused=False, fingerprint=fingerprint, result=result
        )

    def _reuse(
        self,
        run: AgentRun,
        action: InternalActionName,
        key: str,
        fingerprint: str,
    ) -> dict[str, object] | None:
        receipt = self.actions.get_receipt(key)
        if receipt is None:
            return None
        if (
            receipt.agent_run_id != run.id
            or receipt.action_name != action.value
            or receipt.request_fingerprint != fingerprint
        ):
            self._conflict(action, fingerprint, "Idempotency key content conflicts.")
        return dict(receipt.result_payload)

    def _start_action(
        self, run: AgentRun, action: InternalActionName, key: str, fingerprint: str
    ) -> tuple[ToolExecution, float]:
        self.runs.append_event(
            run=run,
            event_type=f"{action.value.removeprefix('create_').removeprefix('save_')}_started",
            step=AgentRunStep.PERSISTING_ACTIONS,
            payload={"action_name": action.value, "fingerprint": fingerprint[:12]},
        )
        execution = self.runs.start_tool_execution(
            run=run,
            tool_name=action.value,
            input_payload={"idempotency_key": key, "fingerprint": fingerprint[:12]},
        )
        return execution, perf_counter()

    def _finish_action(
        self,
        run: AgentRun,
        execution: ToolExecution,
        action: InternalActionName,
        result: Mapping[str, object],
        started: float,
        reused: bool,
    ) -> None:
        duration_ms = max(0, int((perf_counter() - started) * 1000))
        self.runs.finish_tool_execution(
            execution,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"reused": reused, **dict(result)},
            duration_ms=duration_ms,
        )
        event_type = (
            "internal_action_reused"
            if reused
            else {
                InternalActionName.CREATE_CRM_OPPORTUNITY: "crm_opportunity_persisted",
                InternalActionName.CREATE_FOLLOWUP_TASK: "followup_task_persisted",
                InternalActionName.SAVE_CUSTOMER_MEMORY: "customer_memory_persisted",
            }[action]
        )
        self.runs.append_event(
            run=run,
            event_type=event_type,
            step=AgentRunStep.PERSISTING_ACTIONS,
            payload={"action_name": action.value, "reused": reused},
        )

    @staticmethod
    def _conflict(action: InternalActionName, fingerprint: str, message: str) -> None:
        raise InternalActionError(
            code="IDEMPOTENCY_CONFLICT",
            message=message,
            action_name=action,
            fingerprint=fingerprint,
        )

    def _utc_now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The internal-action clock must be timezone-aware.")
        return value.astimezone(UTC)
