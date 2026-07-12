"""Deterministic customer history tool."""

from sqlalchemy.exc import SQLAlchemyError

from app.agent.tools.common import (
    ToolError,
    ToolMeta,
    ToolResponse,
    elapsed_ms,
    started_timer,
)
from app.agent.tools.schemas import CustomerHistoryData, RetrieveCustomerHistoryInput
from app.domain.schemas import (
    CustomerMemoryRecord,
    CustomerRecord,
    OpportunitySummaryRecord,
)
from app.repositories.customers import CustomerRepository


def retrieve_customer_history(
    tool_input: RetrieveCustomerHistoryInput,
    repository: CustomerRepository,
) -> ToolResponse[CustomerHistoryData]:
    """Return explicit active memories and prior opportunities for one customer."""

    started_ns = started_timer()
    customer_id = str(tool_input.customer_id)
    try:
        customer = repository.get(customer_id)
        if customer is None:
            return ToolResponse[CustomerHistoryData](
                success=False,
                data=None,
                error=ToolError(
                    code="NOT_FOUND",
                    message="Customer was not found.",
                    retryable=False,
                ),
                meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
            )

        memories = repository.list_active_memories(
            customer_id=customer_id,
            categories=tool_input.categories,
            limit=tool_input.limit,
        )
        opportunities = repository.list_opportunities(
            customer_id=customer_id,
            limit=tool_input.limit,
        )
        data = CustomerHistoryData(
            customer=CustomerRecord.model_validate(customer),
            memories=[CustomerMemoryRecord.model_validate(memory) for memory in memories],
            opportunities=[
                OpportunitySummaryRecord.model_validate(opportunity)
                for opportunity in opportunities
            ],
        )
        return ToolResponse[CustomerHistoryData](
            success=True,
            data=data,
            error=None,
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
    except SQLAlchemyError:
        return ToolResponse[CustomerHistoryData](
            success=False,
            data=None,
            error=ToolError(
                code="PERSISTENCE_ERROR",
                message="Customer history could not be read.",
                retryable=True,
            ),
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
