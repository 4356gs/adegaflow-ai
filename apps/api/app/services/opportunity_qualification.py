"""Deterministic qualification and content builders for internal actions."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.db.models import Inquiry
from app.domain.analysis import InquiryAnalysis, InquiryIntent
from app.domain.enums import MemoryCategory, OpportunityStage
from app.domain.internal_actions import (
    MemoryFactInput,
    OpportunityActionInput,
    priority_for_score,
)
from app.domain.recommendation import ValidatedRecommendation

_INTENT_POINTS = {
    InquiryIntent.B2B_PURCHASE_INQUIRY: 40,
    InquiryIntent.PRICE_REQUEST: 30,
    InquiryIntent.SAMPLE_REQUEST: 30,
    InquiryIntent.PRODUCT_INFORMATION: 20,
    InquiryIntent.OTHER: 10,
}


def qualification_score(
    analysis: InquiryAnalysis, *, customer_resolved: bool
) -> int:
    score = _INTENT_POINTS[analysis.intent]
    score += 10 if customer_resolved or analysis.company_name else 0
    score += 10 if analysis.market else 0
    score += 10 if analysis.estimated_bottles else 0
    score += 10 if analysis.channel else 0
    score += 10 if analysis.target_date or analysis.target_horizon_days is not None else 0
    score += 5 if analysis.budget_total_cents is not None else 0
    score += 5 if analysis.contact_email else 0
    return min(score, 100)


class OpportunityQualificationService:
    def build(
        self,
        *,
        run_id: str,
        inquiry: Inquiry,
        customer_id: str,
        analysis: InquiryAnalysis,
        recommendation: ValidatedRecommendation,
    ) -> OpportunityActionInput:
        score = qualification_score(analysis, customer_resolved=True)

        market = analysis.market
        if market is None:
            raise ValueError("A market is required to create an opportunity.")
        company_name = analysis.company_name or "Existing customer"
        volume = (
            f"{analysis.estimated_bottles} bottles"
            if analysis.estimated_bottles is not None
            else "volume pending"
        )
        target_date = analysis.target_date
        if target_date is None and analysis.target_horizon_days is not None:
            target_date = inquiry.received_at.date() + timedelta(days=analysis.target_horizon_days)
        channel = analysis.channel or "channel pending"
        summary = (
            "Qualified commercial opportunity for "
            f"{market} via {channel}. Validated recommendation: "
            f"{recommendation.summary}"
        )
        return OpportunityActionInput(
            inquiry_id=UUID(inquiry.id),
            customer_id=UUID(customer_id),
            title=f"{company_name} — {market} — {volume}",
            stage=OpportunityStage.PROPOSAL_DRAFT,
            priority=priority_for_score(score),
            score=score,
            market=market,
            channel=analysis.channel,
            estimated_bottles=analysis.estimated_bottles,
            target_date=target_date,
            summary=summary,
            idempotency_key=f"{run_id}:create_crm_opportunity",
        )


class MemoryExtractionService:
    def build(self, analysis: InquiryAnalysis) -> list[MemoryFactInput]:
        facts: list[MemoryFactInput] = []
        for product in analysis.product_interest:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.PREFERENCE,
                    content=f"Product interest: {product}.",
                )
            )
        if analysis.market:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.PREFERENCE,
                    content=f"Market: {analysis.market}.",
                )
            )
        if analysis.channel:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.PREFERENCE,
                    content=f"Commercial channel: {analysis.channel}.",
                )
            )
        for certification in analysis.certification_requirements:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.REQUIREMENT,
                    content=f"Certification requirement: {certification}.",
                )
            )
        if analysis.delivery_terms:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.REQUIREMENT,
                    content=f"Delivery terms: {analysis.delivery_terms}.",
                )
            )
        if analysis.samples_requested:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.INTERACTION,
                    content="Samples requested.",
                )
            )
        if analysis.price_list_requested:
            facts.append(
                MemoryFactInput(
                    category=MemoryCategory.INTERACTION,
                    content="Price list requested.",
                )
            )
        return facts[:20]
