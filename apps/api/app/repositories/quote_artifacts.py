"""Persistence boundary for deterministic quotes and generated artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    GeneratedArtifact,
    Product,
    Quote,
    QuoteItem,
)
from app.domain.enums import (
    ArtifactType,
    QuoteStatus,
    ReviewStatus,
)

JsonPayload = Mapping[str, object]


class IdempotencyConflictError(RuntimeError):
    """Raised when an existing entity has different authoritative content."""


@dataclass(frozen=True, slots=True)
class QuoteItemInput:
    """Validated quote-line values ready for persistence."""

    product_id: str
    quantity_bottles: int
    unit_price_cents: int
    line_total_cents: int
    cases: int


class QuoteRepository:
    """Persist one deterministic quote per agent run."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, quote_id: str) -> Quote | None:
        return self._session.get(Quote, quote_id)

    def get_by_run_id(self, agent_run_id: str) -> Quote | None:
        statement = select(Quote).where(
            Quote.agent_run_id == agent_run_id
        )
        return self._session.scalar(statement)

    def list_items(self, quote_id: str) -> list[QuoteItem]:
        statement = (
            select(QuoteItem)
            .where(QuoteItem.quote_id == quote_id)
            .order_by(QuoteItem.product_id)
        )
        return list(self._session.scalars(statement))

    def create_or_get(
        self,
        *,
        agent_run_id: str,
        currency: str,
        subtotal_cents: int,
        assumptions: JsonPayload,
        items: Sequence[QuoteItemInput],
        quote_id: str | None = None,
    ) -> tuple[Quote, bool]:
        """Create a quote or reuse an identical quote for the same run."""

        normalized_items = tuple(items)
        self._validate_candidate(
            agent_run_id=agent_run_id,
            currency=currency,
            subtotal_cents=subtotal_cents,
            items=normalized_items,
        )

        existing = self.get_by_run_id(agent_run_id)
        if existing is not None:
            if self._matches(
                existing=existing,
                currency=currency,
                subtotal_cents=subtotal_cents,
                assumptions=assumptions,
                items=normalized_items,
            ):
                return existing, False

            raise IdempotencyConflictError(
                "An existing quote for this run has different content."
            )

        quote = Quote(
            id=quote_id or str(uuid4()),
            agent_run_id=agent_run_id,
            currency=currency,
            subtotal_cents=subtotal_cents,
            status=QuoteStatus.DRAFT.value,
            assumptions=dict(assumptions),
        )
        self._session.add(quote)

        for item in normalized_items:
            self._session.add(
                QuoteItem(
                    id=str(uuid4()),
                    quote_id=quote.id,
                    product_id=item.product_id,
                    quantity_bottles=item.quantity_bottles,
                    unit_price_cents=item.unit_price_cents,
                    line_total_cents=item.line_total_cents,
                    cases=item.cases,
                )
            )

        self._session.flush()
        return quote, True

    def _validate_candidate(
        self,
        *,
        agent_run_id: str,
        currency: str,
        subtotal_cents: int,
        items: Sequence[QuoteItemInput],
    ) -> None:
        if self._session.get(AgentRun, agent_run_id) is None:
            raise LookupError("Agent run does not exist.")

        if currency != "EUR":
            raise ValueError("Only EUR quotes are supported.")

        if subtotal_cents < 0:
            raise ValueError("subtotal_cents must be non-negative.")

        if not items:
            raise ValueError("A quote must contain at least one item.")

        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Quote product IDs must be unique.")

        products = self._session.scalars(
            select(Product.id).where(Product.id.in_(product_ids))
        ).all()
        found_product_ids = set(products)
        missing_product_ids = set(product_ids) - found_product_ids
        if missing_product_ids:
            raise LookupError("One or more quote products do not exist.")

    def _matches(
        self,
        *,
        existing: Quote,
        currency: str,
        subtotal_cents: int,
        assumptions: JsonPayload,
        items: Sequence[QuoteItemInput],
    ) -> bool:
        persisted_items = self.list_items(existing.id)

        expected_items = sorted(
            (
                item.product_id,
                item.quantity_bottles,
                item.unit_price_cents,
                item.line_total_cents,
                item.cases,
            )
            for item in items
        )
        actual_items = [
            (
                item.product_id,
                item.quantity_bottles,
                item.unit_price_cents,
                item.line_total_cents,
                item.cases,
            )
            for item in persisted_items
        ]

        return (
            existing.currency == currency
            and existing.subtotal_cents == subtotal_cents
            and existing.assumptions == dict(assumptions)
            and actual_items == expected_items
        )


class GeneratedArtifactRepository:
    """Persist one artifact of each type per agent run."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        artifact_id: str,
    ) -> GeneratedArtifact | None:
        return self._session.get(GeneratedArtifact, artifact_id)

    def get_by_run_and_type(
        self,
        *,
        agent_run_id: str,
        artifact_type: ArtifactType,
    ) -> GeneratedArtifact | None:
        statement = select(GeneratedArtifact).where(
            GeneratedArtifact.agent_run_id == agent_run_id,
            GeneratedArtifact.artifact_type == artifact_type.value,
        )
        return self._session.scalar(statement)

    def list_by_run(
        self,
        agent_run_id: str,
    ) -> list[GeneratedArtifact]:
        statement = (
            select(GeneratedArtifact)
            .where(GeneratedArtifact.agent_run_id == agent_run_id)
            .order_by(GeneratedArtifact.artifact_type)
        )
        return list(self._session.scalars(statement))

    def create_or_get(
        self,
        *,
        agent_run_id: str,
        quote_id: str,
        artifact_type: ArtifactType,
        language: str,
        schema_version: str,
        content: JsonPayload,
        artifact_id: str | None = None,
    ) -> tuple[GeneratedArtifact, bool]:
        """Create an artifact or reuse an identical persisted artifact."""

        quote = self._session.get(Quote, quote_id)
        if quote is None:
            raise LookupError("Quote does not exist.")

        if quote.agent_run_id != agent_run_id:
            raise ValueError(
                "Artifact quote does not belong to the supplied agent run."
            )

        if (
            len(language) != 2
            or not language.isalpha()
            or language != language.lower()
        ):
            raise ValueError(
                "language must be a lowercase ISO 639-1 code."
            )

        if not schema_version.strip():
            raise ValueError("schema_version must not be empty.")

        existing = self.get_by_run_and_type(
            agent_run_id=agent_run_id,
            artifact_type=artifact_type,
        )
        if existing is not None:
            if (
                existing.quote_id == quote_id
                and existing.language == language
                and existing.schema_version == schema_version
                and existing.content == dict(content)
            ):
                return existing, False

            raise IdempotencyConflictError(
                "An existing artifact of this type has different content."
            )

        artifact = GeneratedArtifact(
            id=artifact_id or str(uuid4()),
            agent_run_id=agent_run_id,
            quote_id=quote_id,
            artifact_type=artifact_type.value,
            language=language,
            schema_version=schema_version,
            content=dict(content),
            review_status=ReviewStatus.NEEDS_REVIEW.value,
        )
        self._session.add(artifact)
        self._session.flush()
        return artifact, True