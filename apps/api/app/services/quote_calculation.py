"""Deterministic quote calculation from a validated recommendation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Inquiry, Quote, QuoteItem
from app.domain.analysis import InquiryAnalysis
from app.domain.quote import (
    CalculatedQuote,
    CalculatedQuoteItem,
    QuoteAssumptions,
)
from app.domain.recommendation import (
    ValidatedRecommendation,
    ValidatedRecommendationItem,
)
from app.repositories.quote_artifacts import (
    IdempotencyConflictError,
    QuoteItemInput,
    QuoteRepository,
)


class QuoteCalculationError(RuntimeError):
    """Safe deterministic quote-calculation error."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        needs_review: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.needs_review = needs_review


@dataclass(frozen=True, slots=True)
class QuoteCalculationResult:
    """Calculated and persisted quote returned to the orchestrator."""

    calculated_quote: CalculatedQuote
    quote: Quote
    items: tuple[QuoteItem, ...]
    created: bool


class QuoteCalculationService:
    """Calculate and persist one reproducible EUR quote per agent run."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = QuoteRepository(session)

    def calculate(
        self,
        agent_run_id: str,
    ) -> QuoteCalculationResult:
        run = self.session.get(AgentRun, agent_run_id)
        if run is None:
            raise QuoteCalculationError(
                code="RUN_NOT_FOUND",
                message="The requested agent run does not exist.",
            )

        recommendation = self._load_recommendation(run)
        budget_total_cents, budget_warning = self._resolve_budget(run)

        calculated_items = [
            self._calculate_item(item)
            for item in recommendation.items
        ]
        subtotal_cents = sum(
            item.line_total_cents for item in calculated_items
        )

        warnings = list(recommendation.warnings)
        if budget_warning is not None:
            warnings.append(budget_warning)

        budget_exceeded = (
            budget_total_cents is not None
            and subtotal_cents > budget_total_cents
        )
        if budget_exceeded:
            warnings.append(
                "Quote subtotal exceeds the known EUR budget."
            )

        calculated_quote = CalculatedQuote(
            agent_run_id=UUID(run.id),
            currency="EUR",
            items=calculated_items,
            subtotal_cents=subtotal_cents,
            budget_total_cents=budget_total_cents,
            budget_exceeded=budget_exceeded,
            warnings=warnings,
            assumptions=QuoteAssumptions(),
        )

        persistence_items = tuple(
            QuoteItemInput(
                product_id=str(item.product_id),
                quantity_bottles=item.quantity_bottles,
                unit_price_cents=item.unit_price_cents,
                line_total_cents=item.line_total_cents,
                cases=item.cases,
            )
            for item in calculated_quote.items
        )

        try:
            quote, created = self.repository.create_or_get(
                agent_run_id=run.id,
                currency=calculated_quote.currency,
                subtotal_cents=calculated_quote.subtotal_cents,
                assumptions=calculated_quote.assumptions.model_dump(
                    mode="json"
                ),
                items=persistence_items,
            )
        except IdempotencyConflictError as exc:
            raise QuoteCalculationError(
                code="QUOTE_IDEMPOTENCY_CONFLICT",
                message=(
                    "A different quote already exists for this agent run."
                ),
                needs_review=True,
            ) from exc
        except (LookupError, ValueError) as exc:
            raise QuoteCalculationError(
                code="QUOTE_INTEGRITY_ERROR",
                message="The quote could not be persisted consistently.",
            ) from exc

        return QuoteCalculationResult(
            calculated_quote=calculated_quote,
            quote=quote,
            items=tuple(self.repository.list_items(quote.id)),
            created=created,
        )

    @staticmethod
    def _load_recommendation(
        run: AgentRun,
    ) -> ValidatedRecommendation:
        payload = run.result_payload
        candidate: object = payload.get("recommendation", payload)

        if not isinstance(candidate, Mapping):
            raise QuoteCalculationError(
                code="RECOMMENDATION_MISSING",
                message=(
                    "The agent run does not contain a validated "
                    "recommendation."
                ),
            )

        currency = candidate.get("currency")
        if currency is not None and currency != "EUR":
            raise QuoteCalculationError(
                code="UNSUPPORTED_QUOTE_CURRENCY",
                message="Only EUR recommendations can be quoted.",
                needs_review=True,
            )

        try:
            recommendation = ValidatedRecommendation.model_validate(
                candidate
            )
        except ValidationError as exc:
            raise QuoteCalculationError(
                code="RECOMMENDATION_INVALID",
                message=(
                    "The agent run recommendation is absent or invalid."
                ),
            ) from exc

        return recommendation

    def _resolve_budget(
        self,
        run: AgentRun,
    ) -> tuple[int | None, str | None]:
        inquiry = self.session.get(Inquiry, run.inquiry_id)
        if inquiry is None:
            raise QuoteCalculationError(
                code="INQUIRY_NOT_FOUND",
                message="The agent run inquiry no longer exists.",
            )

        if not inquiry.extracted_data:
            return None, None

        try:
            analysis = InquiryAnalysis.model_validate(
                inquiry.extracted_data
            )
        except ValidationError as exc:
            raise QuoteCalculationError(
                code="INQUIRY_ANALYSIS_INVALID",
                message=(
                    "The persisted inquiry analysis is not valid."
                ),
            ) from exc

        if analysis.budget_total_cents is None:
            return None, None

        if analysis.budget_currency != "EUR":
            return (
                None,
                "Budget comparison was skipped because the known "
                "budget is not denominated in EUR.",
            )

        return analysis.budget_total_cents, None

    @staticmethod
    def _calculate_item(
        item: ValidatedRecommendationItem,
    ) -> CalculatedQuoteItem:
        try:
            product_id = item.product_id
            sku = item.sku
            name = item.name
            quantity_bottles = item.quantity_bottles
            units_per_case = item.units_per_case
            unit_price_cents = item.unit_price_cents
        except AttributeError as exc:
            raise QuoteCalculationError(
                code="RECOMMENDATION_INVALID",
                message="A recommendation item is incomplete.",
            ) from exc

        if quantity_bottles % units_per_case != 0:
            raise QuoteCalculationError(
                code="QUOTE_ARITHMETIC_ERROR",
                message=(
                    "A recommended quantity is not divisible by "
                    "units per case."
                ),
            )

        cases = quantity_bottles // units_per_case
        line_total_cents = quantity_bottles * unit_price_cents

        try:
            return CalculatedQuoteItem(
                product_id=product_id,
                sku=sku,
                name=name,
                quantity_bottles=quantity_bottles,
                units_per_case=units_per_case,
                cases=cases,
                unit_price_cents=unit_price_cents,
                line_total_cents=line_total_cents,
            )
        except ValidationError as exc:
            raise QuoteCalculationError(
                code="QUOTE_ARITHMETIC_ERROR",
                message=(
                    "A quote line could not be calculated consistently."
                ),
            ) from exc