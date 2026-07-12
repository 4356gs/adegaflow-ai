"""Closed, typed registry for the approved read-only agent tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agent.tools.catalog import (
    check_stock,
    get_product_details,
    search_catalog,
)
from app.agent.tools.common import (
    ToolError,
    ToolMeta,
    ToolResponse,
    elapsed_ms,
)
from app.agent.tools.customers import retrieve_customer_history
from app.agent.tools.schemas import (
    CheckStockInput,
    ProductDetailsInput,
    RetrieveCustomerHistoryInput,
    SearchCatalogInput,
)
from app.db.models import AgentRun
from app.domain.enums import (
    AgentRunStep,
    ToolExecutionStatus,
)
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.customers import CustomerRepository

JsonObject = dict[str, Any]
ToolDefinition = dict[str, Any]
ToolExecutor = Callable[[BaseModel, Session], BaseModel]

REGISTERED_TOOL_NAMES = (
    "search_catalog",
    "get_product_details",
    "check_stock",
    "retrieve_customer_history",
)
SELECTION_TOOL_NAMES = (
    "search_catalog",
    "get_product_details",
    "check_stock",
)


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """One allowlisted tool and its validation/execution contract."""

    name: str
    description: str
    input_model: type[BaseModel]
    executor: ToolExecutor
    max_retries: int = 1

    def as_openai_definition(self) -> ToolDefinition:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


@dataclass(frozen=True, slots=True)
class RegistryExecutionResult:
    """Internal result returned to the bounded orchestrator."""

    execution_id: str
    sequence: int
    tool_name: str
    success: bool
    payload: JsonObject
    error_code: str | None
    retryable: bool


def _run_search_catalog(
    tool_input: BaseModel,
    session: Session,
) -> BaseModel:
    if not isinstance(tool_input, SearchCatalogInput):
        raise TypeError("Invalid validated input for search_catalog.")
    return search_catalog(
        tool_input,
        CatalogRepository(session),
    )


def _run_get_product_details(
    tool_input: BaseModel,
    session: Session,
) -> BaseModel:
    if not isinstance(tool_input, ProductDetailsInput):
        raise TypeError(
            "Invalid validated input for get_product_details."
        )
    return get_product_details(
        tool_input,
        CatalogRepository(session),
    )


def _run_check_stock(
    tool_input: BaseModel,
    session: Session,
) -> BaseModel:
    if not isinstance(tool_input, CheckStockInput):
        raise TypeError("Invalid validated input for check_stock.")
    return check_stock(
        tool_input,
        CatalogRepository(session),
    )


def _run_retrieve_customer_history(
    tool_input: BaseModel,
    session: Session,
) -> BaseModel:
    if not isinstance(tool_input, RetrieveCustomerHistoryInput):
        raise TypeError(
            "Invalid validated input for retrieve_customer_history."
        )
    return retrieve_customer_history(
        tool_input,
        CustomerRepository(session),
    )


def build_registered_tools() -> tuple[RegisteredTool, ...]:
    """Build the immutable MVP allowlist in canonical order."""

    return (
        RegisteredTool(
            name="search_catalog",
            description=(
                "Search active winery products by text, market, "
                "commercial channel and optional maximum unit price."
            ),
            input_model=SearchCatalogInput,
            executor=_run_search_catalog,
        ),
        RegisteredTool(
            name="get_product_details",
            description=(
                "Retrieve complete catalog details for selected active "
                "product identifiers. Inventory is not included."
            ),
            input_model=ProductDetailsInput,
            executor=_run_get_product_details,
        ),
        RegisteredTool(
            name="check_stock",
            description=(
                "Check current sellable bottle stock for requested "
                "product quantities without reserving inventory."
            ),
            input_model=CheckStockInput,
            executor=_run_check_stock,
        ),
        RegisteredTool(
            name="retrieve_customer_history",
            description=(
                "Retrieve one known customer's active explicit memories "
                "and summarized prior opportunities."
            ),
            input_model=RetrieveCustomerHistoryInput,
            executor=_run_retrieve_customer_history,
        ),
    )


class ToolRegistry:
    """Validate, execute and trace only registered read-only tools."""

    def __init__(
        self,
        session: Session,
        run_repository: AgentRunRepository,
        tools: Sequence[RegisteredTool] | None = None,
    ) -> None:
        self._session = session
        self._run_repository = run_repository
        registered = tuple(tools or build_registered_tools())
        names = tuple(tool.name for tool in registered)
        if len(names) != len(set(names)):
            raise ValueError(
                "Registered tool names must be unique."
            )
        if names != REGISTERED_TOOL_NAMES:
            raise ValueError(
                "The MVP registry must contain the canonical allowlist."
            )
        self._tools = {
            tool.name: tool
            for tool in registered
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def definitions(
        self,
        names: Sequence[str] | None = None,
    ) -> list[ToolDefinition]:
        requested = tuple(names or self.names)
        unknown = [
            name
            for name in requested
            if name not in self._tools
        ]
        if unknown:
            raise KeyError(
                f"Unknown registered tool definition: {unknown[0]}"
            )
        return [
            self._tools[name].as_openai_definition()
            for name in requested
        ]

    def selection_definitions(self) -> list[ToolDefinition]:
        return self.definitions(SELECTION_TOOL_NAMES)

    def execute(
        self,
        *,
        run: AgentRun,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> RegistryExecutionResult:
        """Execute one allowlisted tool and persist its trace records."""

        started_ns = perf_counter_ns()
        raw_arguments = dict(arguments)
        step = AgentRunStep(run.current_step)

        self._run_repository.append_event(
            run=run,
            event_type="tool_requested",
            step=step,
            payload={"tool_name": tool_name},
        )

        registered = self._tools.get(tool_name)
        if registered is None:
            return self._reject(
                run=run,
                tool_name=tool_name,
                input_payload=raw_arguments,
                step=step,
                started_ns=started_ns,
                code="UNKNOWN_TOOL",
                message="Requested tool is not registered.",
            )

        try:
            validated_input = registered.input_model.model_validate(
                raw_arguments
            )
        except ValidationError:
            return self._reject(
                run=run,
                tool_name=tool_name,
                input_payload=raw_arguments,
                step=step,
                started_ns=started_ns,
                code="TOOL_INVALID_ARGUMENT",
                message=(
                    "Tool arguments did not match the registered schema."
                ),
            )

        validated_payload = validated_input.model_dump(mode="json")
        execution = self._run_repository.start_tool_execution(
            run=run,
            tool_name=tool_name,
            input_payload=validated_payload,
        )
        self._run_repository.append_event(
            run=run,
            event_type="tool_started",
            step=step,
            payload={
                "tool_name": tool_name,
                "tool_execution_id": execution.id,
                "sequence": execution.sequence,
            },
        )

        try:
            response = registered.executor(
                validated_input,
                self._session,
            )
            payload = response.model_dump(mode="json")
        except Exception:
            payload = self._error_payload(
                code="TOOL_EXECUTION_FAILED",
                message="The registered tool could not be executed.",
                retryable=False,
                duration_ms=elapsed_ms(started_ns),
            )

        success = bool(payload.get("success"))
        error = payload.get("error")
        error_code: str | None = None
        retryable = False
        if isinstance(error, dict):
            raw_code = error.get("code")
            if isinstance(raw_code, str):
                error_code = raw_code
            retryable = bool(error.get("retryable"))

        duration_ms = elapsed_ms(started_ns)
        status = (
            ToolExecutionStatus.SUCCEEDED
            if success
            else ToolExecutionStatus.FAILED
        )
        self._run_repository.finish_tool_execution(
            execution,
            status=status,
            output_payload=payload,
            duration_ms=duration_ms,
            error_code=error_code,
        )
        event_type = (
            "tool_succeeded"
            if success
            else "tool_failed"
        )
        self._run_repository.append_event(
            run=run,
            event_type=event_type,
            step=step,
            payload={
                "tool_name": tool_name,
                "tool_execution_id": execution.id,
                "sequence": execution.sequence,
                "error_code": error_code,
                "duration_ms": duration_ms,
            },
        )

        return RegistryExecutionResult(
            execution_id=execution.id,
            sequence=execution.sequence,
            tool_name=tool_name,
            success=success,
            payload=payload,
            error_code=error_code,
            retryable=retryable,
        )

    def _reject(
        self,
        *,
        run: AgentRun,
        tool_name: str,
        input_payload: JsonObject,
        step: AgentRunStep,
        started_ns: int,
        code: str,
        message: str,
    ) -> RegistryExecutionResult:
        execution = self._run_repository.start_tool_execution(
            run=run,
            tool_name=tool_name,
            input_payload=input_payload,
        )
        duration_ms = elapsed_ms(started_ns)
        payload = self._error_payload(
            code=code,
            message=message,
            retryable=False,
            duration_ms=duration_ms,
        )
        self._run_repository.finish_tool_execution(
            execution,
            status=ToolExecutionStatus.REJECTED,
            output_payload=payload,
            duration_ms=duration_ms,
            error_code=code,
        )
        self._run_repository.append_event(
            run=run,
            event_type="tool_rejected",
            step=step,
            payload={
                "tool_name": tool_name,
                "tool_execution_id": execution.id,
                "sequence": execution.sequence,
                "error_code": code,
            },
        )
        return RegistryExecutionResult(
            execution_id=execution.id,
            sequence=execution.sequence,
            tool_name=tool_name,
            success=False,
            payload=payload,
            error_code=code,
            retryable=False,
        )

    @staticmethod
    def _error_payload(
        *,
        code: str,
        message: str,
        retryable: bool,
        duration_ms: int,
    ) -> JsonObject:
        response = ToolResponse[dict[str, object]](
            success=False,
            data=None,
            error=ToolError(
                code=code,
                message=message,
                retryable=retryable,
            ),
            meta=ToolMeta(duration_ms=duration_ms),
        )
        return response.model_dump(mode="json")
