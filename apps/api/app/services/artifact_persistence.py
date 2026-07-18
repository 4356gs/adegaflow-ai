"""Deterministic assembly and persistence of generated artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    Customer,
    GeneratedArtifact,
    Inquiry,
    Product,
    Quote,
)
from app.domain.analysis import InquiryAnalysis
from app.domain.artifacts import (
    ALLOWED_EMAIL_NEXT_STEPS,
    ALLOWED_PROPOSAL_NEXT_STEPS,
    ArtifactBuyerSnapshot,
    ArtifactQuoteLine,
    ArtifactQuoteSnapshot,
    EmailCommercialBlock,
    EmailDraftArtifactContent,
    EmailDraftNarrative,
    ProposalArtifactContent,
    ProposalNarrative,
)
from app.domain.enums import ArtifactType
from app.domain.quote import QuoteAssumptions
from app.repositories.quote_artifacts import (
    GeneratedArtifactRepository,
    IdempotencyConflictError,
    QuoteRepository,
)


class ArtifactPersistenceError(RuntimeError):
    """Safe deterministic artifact-persistence error."""

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
class ArtifactPersistenceResult:
    """Persisted artifact and its validated structured content."""

    artifact: GeneratedArtifact
    content: ProposalArtifactContent | EmailDraftArtifactContent
    created: bool


@dataclass(frozen=True, slots=True)
class _ArtifactContext:
    run: AgentRun
    inquiry: Inquiry
    customer: Customer | None
    quote: Quote
    language: str
    buyer: ArtifactBuyerSnapshot
    quote_snapshot: ArtifactQuoteSnapshot


class ArtifactPersistenceService:
    """Assemble artifact snapshots without model calls or side effects."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.quote_repository = QuoteRepository(session)
        self.artifact_repository = GeneratedArtifactRepository(session)

    def persist_proposal(
        self,
        *,
        agent_run_id: str,
        quote_id: str,
        narrative: ProposalNarrative,
    ) -> ArtifactPersistenceResult:
        context = self._load_context(
            agent_run_id=agent_run_id,
            quote_id=quote_id,
        )
        if any(
            next_step not in ALLOWED_PROPOSAL_NEXT_STEPS
            for next_step in narrative.next_steps
        ):
            raise ArtifactPersistenceError(
                code="PROPOSAL_NEXT_STEP_NOT_ALLOWED",
                message="The proposal contains an unauthorized next step.",
                needs_review=True,
            )
        quoted_product_ids = {
            line.product_id for line in context.quote_snapshot.lines
        }
        narrative_product_ids = {
            item.product_id for item in narrative.product_positioning
        }
        if not narrative_product_ids.issubset(quoted_product_ids):
            raise ArtifactPersistenceError(
                code="PROPOSAL_PRODUCT_MISMATCH",
                message=(
                    "The proposal references a product outside the quote."
                ),
            )

        content = ProposalArtifactContent(
            language=context.language,
            buyer=context.buyer,
            quote=context.quote_snapshot,
            narrative=narrative,
        )
        return self._persist(
            context=context,
            artifact_type=ArtifactType.PROPOSAL,
            content=content,
        )

    def persist_email_draft(
        self,
        *,
        agent_run_id: str,
        quote_id: str,
        proposal_artifact_id: str,
        narrative: EmailDraftNarrative,
    ) -> ArtifactPersistenceResult:
        context = self._load_context(
            agent_run_id=agent_run_id,
            quote_id=quote_id,
        )
        if narrative.next_step not in ALLOWED_EMAIL_NEXT_STEPS:
            raise ArtifactPersistenceError(
                code="EMAIL_NEXT_STEP_NOT_ALLOWED",
                message="The email draft contains an unauthorized next step.",
                needs_review=True,
            )
        proposal = self.artifact_repository.get_by_id(
            proposal_artifact_id
        )
        if proposal is None:
            raise ArtifactPersistenceError(
                code="PROPOSAL_ARTIFACT_NOT_FOUND",
                message="The required proposal artifact does not exist.",
            )
        if (
            proposal.artifact_type != ArtifactType.PROPOSAL.value
            or proposal.agent_run_id != context.run.id
            or proposal.quote_id != context.quote.id
        ):
            raise ArtifactPersistenceError(
                code="PROPOSAL_ARTIFACT_MISMATCH",
                message=(
                    "The proposal artifact does not match this run and quote."
                ),
            )
        try:
            proposal_id = UUID(proposal.id)
        except ValueError as exc:
            raise ArtifactPersistenceError(
                code="PROPOSAL_ARTIFACT_MISMATCH",
                message="The proposal artifact identifier is invalid.",
            ) from exc

        quote_snapshot = context.quote_snapshot
        commercial_block = EmailCommercialBlock(
            quote_id=quote_snapshot.quote_id,
            currency=quote_snapshot.currency,
            subtotal_cents=quote_snapshot.subtotal_cents,
            status=quote_snapshot.status,
            lines=quote_snapshot.lines,
            assumptions=quote_snapshot.assumptions,
        )
        content = EmailDraftArtifactContent(
            language=context.language,
            recipient=context.buyer,
            proposal_artifact_id=proposal_id,
            commercial_block=commercial_block,
            narrative=narrative,
        )
        return self._persist(
            context=context,
            artifact_type=ArtifactType.EMAIL_DRAFT,
            content=content,
        )

    def _load_context(
        self,
        *,
        agent_run_id: str,
        quote_id: str,
    ) -> _ArtifactContext:
        run = self.session.get(AgentRun, agent_run_id)
        if run is None:
            raise ArtifactPersistenceError(
                code="RUN_NOT_FOUND",
                message="The requested agent run does not exist.",
            )

        inquiry = self.session.get(Inquiry, run.inquiry_id)
        if inquiry is None:
            raise ArtifactPersistenceError(
                code="INQUIRY_NOT_FOUND",
                message="The agent run inquiry does not exist.",
            )

        quote = self.quote_repository.get_by_id(quote_id)
        if quote is None:
            raise ArtifactPersistenceError(
                code="QUOTE_NOT_FOUND",
                message="The requested quote does not exist.",
            )
        if quote.agent_run_id != run.id:
            raise ArtifactPersistenceError(
                code="QUOTE_RUN_MISMATCH",
                message="The quote does not belong to this agent run.",
            )

        customer = (
            self.session.get(Customer, inquiry.customer_id)
            if inquiry.customer_id is not None
            else None
        )
        analysis = self._load_optional_analysis(inquiry.extracted_data)

        try:
            quote_snapshot = self._build_quote_snapshot(quote)
            buyer = self._build_buyer_snapshot(
                customer=customer,
                analysis=analysis,
            )
        except (ValidationError, ValueError) as exc:
            raise ArtifactPersistenceError(
                code="QUOTE_INTEGRITY_ERROR",
                message=(
                    "The quote cannot be assembled into a valid artifact."
                ),
            ) from exc

        return _ArtifactContext(
            run=run,
            inquiry=inquiry,
            customer=customer,
            quote=quote,
            language=self._resolve_language(inquiry, customer),
            buyer=buyer,
            quote_snapshot=quote_snapshot,
        )

    def _build_quote_snapshot(
        self,
        quote: Quote,
    ) -> ArtifactQuoteSnapshot:
        if quote.currency != "EUR":
            raise ValueError("Only EUR quote snapshots are supported.")
        currency: Literal["EUR"] = "EUR"

        if quote.status not in {"draft", "reviewed"}:
            raise ValueError("Quote status is not supported.")
        status: Literal["draft", "reviewed"] = (
            "draft" if quote.status == "draft" else "reviewed"
        )

        items = self.quote_repository.list_items(quote.id)
        if not items:
            raise ValueError("Quote has no lines.")

        product_ids = [item.product_id for item in items]
        products = self.session.scalars(
            select(Product).where(Product.id.in_(product_ids))
        ).all()
        products_by_id = {product.id: product for product in products}
        if set(product_ids) != set(products_by_id):
            raise ValueError("One or more quote products do not exist.")

        lines = [
            ArtifactQuoteLine(
                product_id=UUID(item.product_id),
                sku=products_by_id[item.product_id].sku,
                name=products_by_id[item.product_id].name,
                quantity_bottles=item.quantity_bottles,
                cases=item.cases,
                unit_price_cents=item.unit_price_cents,
                line_total_cents=item.line_total_cents,
            )
            for item in items
        ]
        assumptions = QuoteAssumptions.model_validate(quote.assumptions)
        return ArtifactQuoteSnapshot(
            quote_id=UUID(quote.id),
            currency=currency,
            subtotal_cents=quote.subtotal_cents,
            status=status,
            lines=lines,
            assumptions=assumptions,
        )

    @staticmethod
    def _load_optional_analysis(
        extracted_data: Mapping[str, object],
    ) -> InquiryAnalysis | None:
        if not extracted_data:
            return None
        try:
            return InquiryAnalysis.model_validate(extracted_data)
        except ValidationError:
            return None

    @staticmethod
    def _build_buyer_snapshot(
        *,
        customer: Customer | None,
        analysis: InquiryAnalysis | None,
    ) -> ArtifactBuyerSnapshot:
        return ArtifactBuyerSnapshot(
            company_name=(
                customer.company_name
                if customer is not None
                else analysis.company_name if analysis is not None else None
            ),
            contact_name=(
                customer.contact_name
                if customer is not None and customer.contact_name
                else analysis.contact_name if analysis is not None else None
            ),
            email=(
                customer.email
                if customer is not None and customer.email
                else analysis.contact_email if analysis is not None else None
            ),
            market=analysis.market if analysis is not None else None,
            country_code=(
                customer.country_code if customer is not None else None
            ),
        )

    @classmethod
    def _resolve_language(
        cls,
        inquiry: Inquiry,
        customer: Customer | None,
    ) -> str:
        inquiry_language = cls._valid_language(
            inquiry.detected_language
        )
        if inquiry_language is not None:
            return inquiry_language
        customer_language = cls._valid_language(
            customer.preferred_language if customer is not None else None
        )
        return customer_language or "en"

    @staticmethod
    def _valid_language(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if (
            len(normalized) == 2
            and normalized.isascii()
            and normalized.isalpha()
        ):
            return normalized
        return None

    def _persist(
        self,
        *,
        context: _ArtifactContext,
        artifact_type: ArtifactType,
        content: ProposalArtifactContent | EmailDraftArtifactContent,
    ) -> ArtifactPersistenceResult:
        try:
            artifact, created = self.artifact_repository.create_or_get(
                agent_run_id=context.run.id,
                quote_id=context.quote.id,
                artifact_type=artifact_type,
                language=context.language,
                schema_version=content.schema_version,
                content=content.model_dump(mode="json"),
            )
        except IdempotencyConflictError as exc:
            raise ArtifactPersistenceError(
                code="ARTIFACT_IDEMPOTENCY_CONFLICT",
                message=(
                    "A different artifact of this type already exists "
                    "for the agent run."
                ),
                needs_review=True,
            ) from exc
        except (LookupError, ValueError) as exc:
            raise ArtifactPersistenceError(
                code="QUOTE_INTEGRITY_ERROR",
                message="The artifact could not be persisted consistently.",
            ) from exc

        return ArtifactPersistenceResult(
            artifact=artifact,
            content=content,
            created=created,
        )
