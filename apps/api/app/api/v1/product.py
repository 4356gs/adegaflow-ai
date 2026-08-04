"""Versioned inquiry, asynchronous run, and commercial read endpoints."""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import (
    EMAIL_WRITER_PROMPT_VERSION,
    INQUIRY_ANALYSIS_PROMPT_VERSION,
    PRODUCT_RECOMMENDATION_PROMPT_VERSION,
    PROPOSAL_WRITER_PROMPT_VERSION,
)
from app.api.dependencies import get_session, require_idempotency_key
from app.api.errors import ApiError
from app.api.schemas import (
    AgentRunDetail,
    AgentRunList,
    AgentRunSummary,
    ArtifactPublic,
    CustomerPublic,
    ErrorEnvelope,
    EventList,
    FollowUpPublic,
    InquiryCreate,
    InquiryDetail,
    InquiryList,
    InquirySummary,
    MemoryList,
    MemoryPublic,
    OpportunityDetail,
    OpportunityPublic,
    PublicEvent,
    PublicRunError,
    QuoteItemPublic,
    QuotePublic,
    RunAccepted,
    RunReference,
    RunReferences,
    RunResult,
)
from app.core.config import get_settings
from app.db.models import (
    AgentRun,
    Customer,
    CustomerMemory,
    FollowUpTask,
    GeneratedArtifact,
    Inquiry,
    InternalActionReceipt,
    Opportunity,
    Product,
    Quote,
    QuoteItem,
)
from app.domain.enums import AgentRunStatus, AgentRunStep, InquiryStatus, InternalActionName
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.inquiries import InquiryRepository
from app.repositories.quote_artifacts import GeneratedArtifactRepository, QuoteRepository
from app.services.async_runs import (
    TERMINAL_STATUSES,
    QueueFullError,
    RunDispatcher,
    is_retryable,
)

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]
KeyDep = Annotated[str, Depends(require_idempotency_key)]

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    503: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
}
PROMPT_VERSIONS: dict[str, object] = {
    "inquiry_analysis": INQUIRY_ANALYSIS_PROMPT_VERSION,
    "product_recommendation": PRODUCT_RECOMMENDATION_PROMPT_VERSION,
    "proposal_writer": PROPOSAL_WRITER_PROMPT_VERSION,
    "email_writer": EMAIL_WRITER_PROMPT_VERSION,
}


def _dispatcher(request: Request) -> RunDispatcher:
    dispatcher = getattr(request.app.state, "run_dispatcher", None)
    if dispatcher is None:
        raise ApiError(503, "DISPATCH_FAILED", "The run dispatcher is unavailable.")
    return dispatcher


def _accepted(run: AgentRun) -> RunAccepted:
    return RunAccepted(
        agent_run_id=UUID(run.id),
        inquiry_id=UUID(run.inquiry_id),
        status=AgentRunStatus(run.status),
        current_step=AgentRunStep(run.current_step),
        correlation_id=UUID(run.correlation_id),
        retry_of_run_id=UUID(run.retry_of_run_id) if run.retry_of_run_id else None,
        poll_url=f"/api/v1/agent-runs/{run.id}",
    )


def _inquiry_summary(inquiry: Inquiry) -> InquirySummary:
    return InquirySummary.model_validate(inquiry)


def _commercial_records(
    session: Session, run_id: str
) -> tuple[Opportunity | None, FollowUpTask | None]:
    receipts = list(
        session.scalars(
            select(InternalActionReceipt).where(
                InternalActionReceipt.agent_run_id == run_id,
                InternalActionReceipt.action_name.in_(
                    [
                        InternalActionName.CREATE_CRM_OPPORTUNITY.value,
                        InternalActionName.CREATE_FOLLOWUP_TASK.value,
                    ]
                ),
            )
        )
    )
    by_action = {item.action_name: item.result_payload for item in receipts}
    opportunity_payload = by_action.get(InternalActionName.CREATE_CRM_OPPORTUNITY.value, {})
    followup_payload = by_action.get(InternalActionName.CREATE_FOLLOWUP_TASK.value, {})
    opportunity_id = opportunity_payload.get("opportunity_id")
    followup_id = followup_payload.get("followup_task_id")
    opportunity = (
        session.get(Opportunity, opportunity_id) if isinstance(opportunity_id, str) else None
    )
    followup = session.get(FollowUpTask, followup_id) if isinstance(followup_id, str) else None
    return opportunity, followup


def _run_references(session: Session, run: AgentRun) -> RunReferences:
    quote = QuoteRepository(session).get_by_run_id(run.id)
    artifacts = GeneratedArtifactRepository(session).list_by_run(run.id)
    opportunity, followup = _commercial_records(session, run.id)
    return RunReferences(
        quote_id=UUID(quote.id) if quote else None,
        proposal_id=next(
            (UUID(item.id) for item in artifacts if item.artifact_type == "proposal"), None
        ),
        email_draft_id=next(
            (UUID(item.id) for item in artifacts if item.artifact_type == "email_draft"),
            None,
        ),
        opportunity_id=UUID(opportunity.id) if opportunity else None,
        followup_task_id=UUID(followup.id) if followup else None,
    )


def _inquiry_detail(session: Session, inquiry: Inquiry) -> InquiryDetail:
    runs = AgentRunRepository(session).list_runs(inquiry_id=inquiry.id, limit=100, offset=0)
    return InquiryDetail(
        **_inquiry_summary(inquiry).model_dump(),
        raw_message=inquiry.raw_message,
        extracted_data=dict(inquiry.extracted_data),
        missing_fields=list(inquiry.missing_fields),
        agent_runs=[RunReference.model_validate(item) for item in runs],
    )


def _quote_public(session: Session, quote: Quote | None) -> QuotePublic | None:
    if quote is None:
        return None
    rows = session.execute(
        select(QuoteItem, Product)
        .join(Product, Product.id == QuoteItem.product_id)
        .where(QuoteItem.quote_id == quote.id)
        .order_by(Product.sku)
    ).all()
    return QuotePublic(
        id=UUID(quote.id),
        currency=cast("Literal['EUR']", quote.currency),
        subtotal_cents=quote.subtotal_cents,
        status=quote.status,
        assumptions=dict(quote.assumptions),
        items=[
            QuoteItemPublic(
                product_id=item.product_id,
                sku=product.sku,
                name=product.name,
                quantity_bottles=item.quantity_bottles,
                unit_price_cents=item.unit_price_cents,
                line_total_cents=item.line_total_cents,
                cases=item.cases,
            )
            for item, product in rows
        ],
    )


def _artifact_public(item: GeneratedArtifact) -> ArtifactPublic:
    return ArtifactPublic.model_validate(item)


def _memory_public(item: CustomerMemory) -> MemoryPublic:
    return MemoryPublic.model_validate(item)


def _public_event_payload(payload: dict[str, object]) -> dict[str, object]:
    allowed = {
        "error_code",
        "reason",
        "schema_version",
        "missing_field_count",
        "model_round",
        "tool_call_count",
        "validation_status",
        "quote_id",
        "artifact_id",
        "artifact_type",
        "opportunity_id",
        "followup_task_id",
        "memory_id",
        "action_name",
        "tool_name",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def _dispatch_or_fail(*, session: Session, dispatcher: RunDispatcher, run: AgentRun) -> None:
    try:
        dispatcher.enqueue(run.id)
    except QueueFullError as exc:
        repository = AgentRunRepository(session)
        repository.fail_run(
            run,
            error_code="DISPATCH_QUEUE_FULL",
            message_safe="The local run queue is temporarily full.",
        )
        repository.append_event(
            run=run,
            event_type="dispatch_failed",
            step=AgentRunStep.FAILED,
            payload={"error_code": "DISPATCH_QUEUE_FULL"},
        )
        session.commit()
        raise ApiError(
            503,
            "DISPATCH_QUEUE_FULL",
            "The local run queue is temporarily full.",
            details={"agent_run_id": run.id},
        ) from exc
    except Exception as exc:
        repository = AgentRunRepository(session)
        repository.fail_run(
            run,
            error_code="DISPATCH_FAILED",
            message_safe="The agent run could not be dispatched.",
        )
        repository.append_event(
            run=run,
            event_type="dispatch_failed",
            step=AgentRunStep.FAILED,
            payload={"error_code": "DISPATCH_FAILED"},
        )
        session.commit()
        raise ApiError(
            503,
            "DISPATCH_FAILED",
            "The agent run could not be dispatched.",
            details={"agent_run_id": run.id},
        ) from exc


@router.post(
    "/inquiries",
    response_model=InquirySummary,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": InquirySummary}, **ERROR_RESPONSES},
    tags=["inquiries"],
)
def create_inquiry(
    payload: InquiryCreate,
    response: Response,
    session: SessionDep,
    idempotency_key: KeyDep,
) -> InquirySummary:
    repository = InquiryRepository(session)
    existing = repository.get_by_submission_key(idempotency_key)
    customer_id = str(payload.customer_id) if payload.customer_id else None
    if existing is not None:
        if (
            existing.source != payload.source
            or existing.raw_message != payload.raw_message
            or existing.customer_id != customer_id
        ):
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key was already used for another inquiry.",
            )
        response.status_code = status.HTTP_200_OK
        return _inquiry_summary(existing)
    if customer_id is not None and session.get(Customer, customer_id) is None:
        raise ApiError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
    inquiry = repository.create(
        source=payload.source,
        raw_message=payload.raw_message,
        customer_id=customer_id,
        submission_key=idempotency_key,
    )
    session.commit()
    return _inquiry_summary(inquiry)


@router.get(
    "/inquiries",
    response_model=InquiryList,
    responses=ERROR_RESPONSES,
    tags=["inquiries"],
)
def list_inquiries(
    session: SessionDep,
    status_filter: InquiryStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> InquiryList:
    items = InquiryRepository(session).list_inquiries(
        status=status_filter, limit=limit, offset=offset
    )
    return InquiryList(items=[_inquiry_summary(item) for item in items], limit=limit, offset=offset)


@router.get(
    "/inquiries/{inquiry_id}",
    response_model=InquiryDetail,
    responses=ERROR_RESPONSES,
    tags=["inquiries"],
)
def get_inquiry(inquiry_id: UUID, session: SessionDep) -> InquiryDetail:
    inquiry = session.get(Inquiry, str(inquiry_id))
    if inquiry is None:
        raise ApiError(404, "INQUIRY_NOT_FOUND", "Inquiry was not found.")
    return _inquiry_detail(session, inquiry)


@router.post(
    "/inquiries/{inquiry_id}/agent-runs",
    response_model=RunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def create_agent_run(
    inquiry_id: UUID,
    request: Request,
    session: SessionDep,
    idempotency_key: KeyDep,
) -> RunAccepted:
    repository = AgentRunRepository(session)
    existing = repository.get_by_request_key(idempotency_key)
    if existing is not None:
        if existing.inquiry_id != str(inquiry_id) or existing.retry_of_run_id is not None:
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key was already used for another run command.",
            )
        return _accepted(existing)
    inquiry = session.get(Inquiry, str(inquiry_id))
    if inquiry is None:
        raise ApiError(404, "INQUIRY_NOT_FOUND", "Inquiry was not found.")
    active = repository.list_runs(inquiry_id=str(inquiry_id), limit=100, offset=0)
    if any(item.status in {"queued", "running"} for item in active):
        raise ApiError(409, "RUN_ALREADY_ACTIVE", "Inquiry already has an active run.")
    settings = get_settings()
    run = repository.create_run(
        inquiry_id=str(inquiry_id),
        model=settings.qwen_model,
        prompt_versions=PROMPT_VERSIONS,
        request_key=idempotency_key,
    )
    repository.append_event(
        run=run,
        event_type="run_created",
        step=AgentRunStep.QUEUED,
        payload={},
    )
    session.commit()
    _dispatch_or_fail(session=session, dispatcher=_dispatcher(request), run=run)
    return _accepted(run)


@router.get(
    "/agent-runs",
    response_model=AgentRunList,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def list_agent_runs(
    session: SessionDep,
    status_filter: AgentRunStatus | None = Query(default=None, alias="status"),
    inquiry_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> AgentRunList:
    repository = AgentRunRepository(session)
    runs = repository.list_runs(
        status=status_filter,
        inquiry_id=str(inquiry_id) if inquiry_id else None,
        limit=limit,
        offset=offset,
    )
    items: list[AgentRunSummary] = []
    for run in runs:
        inquiry = session.get(Inquiry, run.inquiry_id)
        customer = (
            session.get(Customer, inquiry.customer_id) if inquiry and inquiry.customer_id else None
        )
        extracted = inquiry.extracted_data if inquiry else {}
        market = extracted.get("market") if isinstance(extracted, dict) else None
        items.append(
            AgentRunSummary(
                id=UUID(run.id),
                inquiry_id=UUID(run.inquiry_id),
                retry_of_run_id=(UUID(run.retry_of_run_id) if run.retry_of_run_id else None),
                status=AgentRunStatus(run.status),
                current_step=AgentRunStep(run.current_step),
                company_name=customer.company_name if customer else None,
                market=market if isinstance(market, str) else None,
                received_at=inquiry.received_at if inquiry else run.started_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
                error_code=run.error_code,
                retryable=is_retryable(status=run.status, error_code=run.error_code),
            )
        )
    return AgentRunList(items=items, limit=limit, offset=offset)


@router.get(
    "/agent-runs/{agent_run_id}",
    response_model=AgentRunDetail,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def get_agent_run(agent_run_id: UUID, session: SessionDep) -> AgentRunDetail:
    repository = AgentRunRepository(session)
    run = repository.get_by_id(str(agent_run_id))
    if run is None:
        raise ApiError(404, "AGENT_RUN_NOT_FOUND", "Agent run was not found.")
    return AgentRunDetail(
        id=UUID(run.id),
        inquiry_id=UUID(run.inquiry_id),
        retry_of_run_id=UUID(run.retry_of_run_id) if run.retry_of_run_id else None,
        correlation_id=UUID(run.correlation_id),
        status=AgentRunStatus(run.status),
        current_step=AgentRunStep(run.current_step),
        started_at=run.started_at,
        completed_at=run.completed_at,
        model=run.model,
        prompt_versions=dict(run.prompt_versions),
        error=(
            PublicRunError(code=run.error_code, message=run.error_message_safe or "")
            if run.error_code
            else None
        ),
        retryable=is_retryable(status=run.status, error_code=run.error_code),
        references=_run_references(session, run),
        last_event_sequence=repository.last_event_sequence(run.id),
        events_url=f"/api/v1/agent-runs/{run.id}/events",
        result_url=f"/api/v1/agent-runs/{run.id}/result",
    )


@router.get(
    "/agent-runs/{agent_run_id}/events",
    response_model=EventList,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def get_agent_run_events(
    agent_run_id: UUID,
    session: SessionDep,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
) -> EventList:
    repository = AgentRunRepository(session)
    run = repository.get_by_id(str(agent_run_id))
    if run is None:
        raise ApiError(404, "AGENT_RUN_NOT_FOUND", "Agent run was not found.")
    events = repository.list_events(run.id, after_sequence=after_sequence, limit=limit)
    return EventList(
        agent_run_id=UUID(run.id),
        events=[
            PublicEvent(
                sequence=item.sequence,
                event_type=item.event_type,
                step=AgentRunStep(item.step),
                payload=_public_event_payload(item.payload),
                created_at=item.created_at,
            )
            for item in events
        ],
        last_sequence=events[-1].sequence if events else after_sequence,
        terminal=run.status in TERMINAL_STATUSES,
    )


@router.post(
    "/agent-runs/{agent_run_id}/retry",
    response_model=RunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def retry_agent_run(
    agent_run_id: UUID,
    request: Request,
    session: SessionDep,
    idempotency_key: KeyDep,
) -> RunAccepted:
    repository = AgentRunRepository(session)
    existing = repository.get_by_request_key(idempotency_key)
    if existing is not None:
        if existing.retry_of_run_id != str(agent_run_id):
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key was already used for another retry command.",
            )
        return _accepted(existing)
    original = repository.get_by_id(str(agent_run_id))
    if original is None:
        raise ApiError(404, "AGENT_RUN_NOT_FOUND", "Agent run was not found.")
    if not is_retryable(status=original.status, error_code=original.error_code):
        raise ApiError(409, "RUN_NOT_RETRYABLE", "The agent run cannot be retried.")
    settings = get_settings()
    run = repository.create_run(
        inquiry_id=original.inquiry_id,
        model=settings.qwen_model,
        prompt_versions=PROMPT_VERSIONS,
        request_key=idempotency_key,
        retry_of_run_id=original.id,
    )
    repository.append_event(
        run=run,
        event_type="run_created",
        step=AgentRunStep.QUEUED,
        payload={},
    )
    session.commit()
    _dispatch_or_fail(session=session, dispatcher=_dispatcher(request), run=run)
    return _accepted(run)


@router.get(
    "/agent-runs/{agent_run_id}/result",
    response_model=RunResult,
    responses=ERROR_RESPONSES,
    tags=["agent-runs"],
)
def get_agent_run_result(agent_run_id: UUID, session: SessionDep) -> RunResult:
    run = session.get(AgentRun, str(agent_run_id))
    if run is None:
        raise ApiError(404, "AGENT_RUN_NOT_FOUND", "Agent run was not found.")
    if run.status not in TERMINAL_STATUSES:
        raise ApiError(409, "RUN_NOT_TERMINAL", "The agent run is not terminal.")
    inquiry = session.get(Inquiry, run.inquiry_id)
    if inquiry is None:
        raise ApiError(404, "INQUIRY_NOT_FOUND", "Inquiry was not found.")
    quote = QuoteRepository(session).get_by_run_id(run.id)
    artifacts = GeneratedArtifactRepository(session).list_by_run(run.id)
    customer = session.get(Customer, inquiry.customer_id) if inquiry.customer_id else None
    opportunity, followup = _commercial_records(session, run.id)
    memories = []
    if customer is not None:
        memories = list(
            session.scalars(
                select(CustomerMemory)
                .where(
                    CustomerMemory.customer_id == customer.id,
                    CustomerMemory.is_active.is_(True),
                )
                .order_by(CustomerMemory.created_at.desc(), CustomerMemory.id.desc())
                .limit(100)
            )
        )
    result = run.result_payload if isinstance(run.result_payload, dict) else {}
    warnings = result.get("warnings", [])
    recommendation = result.get("recommendation")
    public_recommendation = dict(recommendation) if isinstance(recommendation, dict) else None
    return RunResult(
        agent_run_id=UUID(run.id),
        status=AgentRunStatus(run.status),
        inquiry=_inquiry_detail(session, inquiry),
        analysis=dict(inquiry.extracted_data) if inquiry.extracted_data else None,
        recommendation=public_recommendation,
        quote=_quote_public(session, quote),
        artifacts=[_artifact_public(item) for item in artifacts],
        customer=CustomerPublic.model_validate(customer) if customer else None,
        opportunity=OpportunityPublic.model_validate(opportunity) if opportunity else None,
        followup=FollowUpPublic.model_validate(followup) if followup else None,
        memory_summary=[_memory_public(item) for item in memories],
        warnings=[item for item in warnings if isinstance(item, str)]
        if isinstance(warnings, list)
        else [],
    )


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityDetail,
    responses=ERROR_RESPONSES,
    tags=["opportunities"],
)
def get_opportunity(opportunity_id: UUID, session: SessionDep) -> OpportunityDetail:
    opportunity = session.get(Opportunity, str(opportunity_id))
    if opportunity is None:
        raise ApiError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity was not found.")
    customer = session.get(Customer, opportunity.customer_id)
    if customer is None:
        raise ApiError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.inquiry_id == opportunity.inquiry_id)
        .order_by(AgentRun.started_at.desc())
    )
    quote = QuoteRepository(session).get_by_run_id(run.id) if run else None
    artifacts = GeneratedArtifactRepository(session).list_by_run(run.id) if run else []
    followup = session.scalar(
        select(FollowUpTask).where(FollowUpTask.opportunity_id == opportunity.id)
    )
    return OpportunityDetail(
        **OpportunityPublic.model_validate(opportunity).model_dump(),
        customer=CustomerPublic.model_validate(customer),
        quote=_quote_public(session, quote),
        artifacts=[_artifact_public(item) for item in artifacts],
        followup=FollowUpPublic.model_validate(followup) if followup else None,
    )


@router.get(
    "/customers/{customer_id}/memory",
    response_model=MemoryList,
    responses=ERROR_RESPONSES,
    tags=["customers"],
)
def get_customer_memory(
    customer_id: UUID,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> MemoryList:
    if session.get(Customer, str(customer_id)) is None:
        raise ApiError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
    memories = list(
        session.scalars(
            select(CustomerMemory)
            .where(
                CustomerMemory.customer_id == str(customer_id),
                CustomerMemory.is_active.is_(True),
            )
            .order_by(CustomerMemory.created_at.desc(), CustomerMemory.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return MemoryList(
        customer_id=customer_id,
        items=[_memory_public(item) for item in memories],
        limit=limit,
        offset=offset,
    )
