from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from app.agent.tools.catalog import (
    check_stock,
    get_product_details,
    search_catalog,
)
from app.agent.tools.schemas import (
    CheckStockInput,
    ProductDetailsInput,
    SearchCatalogInput,
)
from app.domain.recommendation import (
    RecommendationContext,
    RecommendationDraft,
    RecommendationDraftItem,
    RecommendationEvidence,
    StockEvidence,
)
from app.repositories.catalog import CatalogRepository
from app.services.recommendation_validation import (
    RecommendationValidationService,
)
from sqlalchemy.orm import Session

PRODUCT_ONE = UUID("11111111-1111-4111-8111-111111111111")
PRODUCT_TWO = UUID("22222222-2222-4222-8222-222222222222")
PRODUCT_THREE = UUID("33333333-3333-4333-8333-333333333333")
PRODUCT_FOUR = UUID("44444444-4444-4444-8444-444444444444")
UNKNOWN_PRODUCT = UUID("99999999-9999-4999-8999-999999999999")


def _draft(
    quantities: list[tuple[UUID, int]],
) -> RecommendationDraft:
    return RecommendationDraft(
        items=[
            RecommendationDraftItem(
                product_id=product_id,
                quantity_bottles=quantity,
                rationale="Supported by the requested market and channel.",
            )
            for product_id, quantity in quantities
        ],
        summary="Validated candidate recommendation.",
        warnings=[],
    )


def _context(
    *,
    estimated_bottles: int = 600,
    requested_references: int = 2,
    required_certifications: list[str] | None = None,
) -> RecommendationContext:
    return RecommendationContext(
        market="DE",
        channel="specialty_retail",
        product_interest="Albariño",
        estimated_bottles=estimated_bottles,
        requested_references=requested_references,
        required_certifications=required_certifications or [],
    )


def _evidence(
    db_session: Session,
    quantities: list[tuple[UUID, int]],
    *,
    retrieved_ids: Iterable[UUID] | None = None,
    include_stock: bool = True,
) -> RecommendationEvidence:
    repository = CatalogRepository(db_session)
    product_ids = list(dict.fromkeys(product_id for product_id, _ in quantities))

    details = get_product_details(
        ProductDetailsInput(product_ids=product_ids),
        repository,
    )
    assert details.success is True
    assert details.data is not None

    stock_items: list[StockEvidence] = []
    if include_stock:
        stock = check_stock(
            CheckStockInput(
                items=[
                    {
                        "product_id": product_id,
                        "requested_bottles": quantity,
                    }
                    for product_id, quantity in quantities
                ]
            ),
            repository,
        )
        if stock.success:
            assert stock.data is not None
            stock_items = [
                StockEvidence.model_validate(
                    item.model_dump(mode="json")
                )
                for item in stock.data.items
            ]

    return RecommendationEvidence(
        retrieved_product_ids=list(
            retrieved_ids
            if retrieved_ids is not None
            else product_ids
        ),
        products=details.data.products,
        stock_items=stock_items,
    )


def _main_scenario_evidence(
    db_session: Session,
) -> RecommendationEvidence:
    repository = CatalogRepository(db_session)
    search = search_catalog(
        SearchCatalogInput(
            query="Albariño",
            market="DE",
            channel="specialty_retail",
            limit=20,
        ),
        repository,
    )
    assert search.success is True
    assert search.data is not None
    retrieved_ids = [
        UUID(item.product_id)
        for item in search.data.items
    ]
    return _evidence(
        db_session,
        [
            (PRODUCT_ONE, 300),
            (PRODUCT_TWO, 300),
        ],
        retrieved_ids=retrieved_ids,
    )


def _issue_codes(outcome: object) -> set[str]:
    issues = outcome.issues
    return {issue.code for issue in issues}


def test_validates_and_enriches_two_reference_600_bottle_scenario(
    db_session: Session,
) -> None:
    outcome = RecommendationValidationService().validate(
        draft=_draft(
            [
                (PRODUCT_ONE, 300),
                (PRODUCT_TWO, 300),
            ]
        ),
        context=_context(),
        evidence=_main_scenario_evidence(db_session),
    )

    assert outcome.valid is True
    assert outcome.issues == []
    assert outcome.result is not None
    assert outcome.result.total_bottles == 600
    assert len(outcome.result.items) == 2

    first, second = outcome.result.items
    assert first.sku == "ADA-ALB-JOV-2025"
    assert first.name == "Brétema Albariño 2025"
    assert first.units_per_case == 6
    assert first.cases == 50
    assert first.unit_price_cents == 840
    assert first.sellable_bottles == 1200

    assert second.sku == "ADA-ALB-LIA-2024"
    assert second.cases == 50
    assert second.unit_price_cents == 1190
    assert second.sellable_bottles == 720

    payload = outcome.result.model_dump(mode="json")
    assert "subtotal" not in payload
    assert "total_cents" not in payload
    assert "quote" not in payload


def test_rejects_incorrect_total_volume(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 294),
        (PRODUCT_TWO, 300),
    ]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(),
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is False
    assert "TOTAL_BOTTLES_MISMATCH" in _issue_codes(outcome)
    assert outcome.correction_payload()["errors"]


def test_rejects_quantities_not_divisible_by_case(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 301),
        (PRODUCT_TWO, 299),
    ]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(),
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is False
    assert "QUANTITY_NOT_CASE_DIVISIBLE" in _issue_codes(outcome)


def test_rejects_duplicate_product(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 300),
        (PRODUCT_ONE, 300),
    ]
    evidence = _evidence(
        db_session,
        [(PRODUCT_ONE, 600)],
    )
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(),
        evidence=evidence,
    )

    assert outcome.valid is False
    assert "DUPLICATE_PRODUCT" in _issue_codes(outcome)


def test_rejects_product_not_retrieved_during_run(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 300),
        (PRODUCT_THREE, 300),
    ]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(),
        evidence=_evidence(
            db_session,
            quantities,
            retrieved_ids=[PRODUCT_ONE],
        ),
    )

    assert outcome.valid is False
    assert "PRODUCT_NOT_RETRIEVED" in _issue_codes(outcome)


def test_rejects_product_without_authoritative_details(
    db_session: Session,
) -> None:
    evidence = RecommendationEvidence(
        retrieved_product_ids=[UNKNOWN_PRODUCT],
        products=[],
        stock_items=[],
    )
    outcome = RecommendationValidationService().validate(
        draft=_draft([(UNKNOWN_PRODUCT, 600)]),
        context=_context(requested_references=1),
        evidence=evidence,
    )

    assert outcome.valid is False
    codes = _issue_codes(outcome)
    assert "PRODUCT_NOT_FOUND" in codes
    assert "STOCK_NOT_CHECKED" not in codes


def test_rejects_insufficient_stock(
    db_session: Session,
) -> None:
    quantities = [(PRODUCT_FOUR, 102)]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(
            estimated_bottles=102,
            requested_references=1,
        ),
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is False
    assert "INSUFFICIENT_STOCK" in _issue_codes(outcome)


def test_rejects_missing_required_certification(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 300),
        (PRODUCT_TWO, 300),
    ]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=_context(
            required_certifications=["organic"]
        ),
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is False
    assert "CERTIFICATION_MISSING" in _issue_codes(outcome)


def test_rejects_market_or_channel_mismatch(
    db_session: Session,
) -> None:
    quantities = [(PRODUCT_FOUR, 96)]
    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=RecommendationContext(
            market="ES",
            channel="hospitality",
            product_interest="Albariño",
            estimated_bottles=96,
            requested_references=1,
        ),
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is False
    codes = _issue_codes(outcome)
    assert "MARKET_MISMATCH" in codes
    assert "CHANNEL_MISMATCH" in codes


def test_adds_warning_when_budget_cannot_be_applied(
    db_session: Session,
) -> None:
    quantities = [
        (PRODUCT_ONE, 300),
        (PRODUCT_TWO, 300),
    ]
    context = _context()
    context.budget_total_cents = 900_000
    context.budget_currency = "USD"

    outcome = RecommendationValidationService().validate(
        draft=_draft(quantities),
        context=context,
        evidence=_evidence(db_session, quantities),
    )

    assert outcome.valid is True
    assert outcome.result is not None
    assert outcome.result.warnings == ["BUDGET_NOT_APPLIED"]
