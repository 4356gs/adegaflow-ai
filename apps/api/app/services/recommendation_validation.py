"""Deterministic enrichment and validation for product recommendations."""

from __future__ import annotations

from collections import Counter
from unicodedata import combining, normalize
from uuid import UUID

from app.domain.recommendation import (
    RecommendationContext,
    RecommendationDraft,
    RecommendationEvidence,
    RecommendationValidationIssue,
    RecommendationValidationOutcome,
    StockEvidence,
    ValidatedRecommendation,
    ValidatedRecommendationItem,
)
from app.domain.schemas import ProductRecord


def _normalized(value: str) -> str:
    decomposed = normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in decomposed
        if not combining(character)
    )


class RecommendationValidationService:
    """Apply all authoritative product, quantity and stock rules."""

    def validate(
        self,
        *,
        draft: RecommendationDraft,
        context: RecommendationContext,
        evidence: RecommendationEvidence,
    ) -> RecommendationValidationOutcome:
        issues: list[RecommendationValidationIssue] = []
        warnings = list(draft.warnings)

        products_by_id, product_conflicts = self._products_by_id(
            evidence.products
        )
        stock_by_id, stock_conflicts = self._stock_by_id(
            evidence.stock_items
        )
        retrieved_ids = set(evidence.retrieved_product_ids)

        for product_id in product_conflicts:
            issues.append(
                self._issue(
                    code="EVIDENCE_CONFLICT",
                    path="evidence.products",
                    message=(
                        "Conflicting product details were collected "
                        "for one product."
                    ),
                    correctable=False,
                    product_id=product_id,
                )
            )

        for product_id in stock_conflicts:
            issues.append(
                self._issue(
                    code="EVIDENCE_CONFLICT",
                    path="evidence.stock_items",
                    message=(
                        "Conflicting stock observations were collected "
                        "for one product."
                    ),
                    correctable=False,
                    product_id=product_id,
                )
            )

        item_counts = Counter(item.product_id for item in draft.items)
        for product_id, count in item_counts.items():
            if count > 1:
                issues.append(
                    self._issue(
                        code="DUPLICATE_PRODUCT",
                        path="items",
                        message=(
                            "A product may appear only once in a "
                            "recommendation."
                        ),
                        correctable=True,
                        product_id=product_id,
                    )
                )

        if (
            context.requested_references is not None
            and len(draft.items) != context.requested_references
        ):
            issues.append(
                self._issue(
                    code="REFERENCE_COUNT_MISMATCH",
                    path="items",
                    message=(
                        "The recommendation does not contain the "
                        "requested number of product references."
                    ),
                    correctable=True,
                )
            )

        total_bottles = sum(
            item.quantity_bottles
            for item in draft.items
        )
        if (
            context.estimated_bottles is not None
            and total_bottles != context.estimated_bottles
        ):
            issues.append(
                self._issue(
                    code="TOTAL_BOTTLES_MISMATCH",
                    path="items",
                    message=(
                        "Recommended quantities do not equal the "
                        "requested bottle volume."
                    ),
                    correctable=True,
                )
            )

        validated_items: list[ValidatedRecommendationItem] = []
        for index, item in enumerate(draft.items):
            path = f"items.{index}"
            product = products_by_id.get(item.product_id)
            stock = stock_by_id.get(item.product_id)

            if item.product_id not in retrieved_ids:
                issues.append(
                    self._issue(
                        code="PRODUCT_NOT_RETRIEVED",
                        path=f"{path}.product_id",
                        message=(
                            "The selected product was not returned by "
                            "catalog tools during this run."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )

            if product is None:
                issues.append(
                    self._issue(
                        code="PRODUCT_NOT_FOUND",
                        path=f"{path}.product_id",
                        message=(
                            "Authoritative product details are missing "
                            "for the selected product."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )
                continue

            if not product.active:
                issues.append(
                    self._issue(
                        code="PRODUCT_INACTIVE",
                        path=f"{path}.product_id",
                        message=(
                            "The selected product is not active."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )

            if item.quantity_bottles % product.units_per_case != 0:
                issues.append(
                    self._issue(
                        code="QUANTITY_NOT_CASE_DIVISIBLE",
                        path=f"{path}.quantity_bottles",
                        message=(
                            "The bottle quantity must be divisible by "
                            "the product case size."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )

            self._validate_market_and_channel(
                product=product,
                context=context,
                path=path,
                issues=issues,
            )
            self._validate_product_interest(
                product=product,
                context=context,
                path=path,
                issues=issues,
            )
            self._validate_certifications(
                product=product,
                context=context,
                path=path,
                issues=issues,
            )

            if stock is None:
                issues.append(
                    self._issue(
                        code="STOCK_NOT_CHECKED",
                        path=f"{path}.product_id",
                        message=(
                            "No authoritative stock observation exists "
                            "for the selected product."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )
                continue

            if stock.requested_bottles != item.quantity_bottles:
                issues.append(
                    self._issue(
                        code="STOCK_REQUEST_MISMATCH",
                        path=f"{path}.quantity_bottles",
                        message=(
                            "The stock check quantity does not match "
                            "the recommendation quantity."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )

            if (
                not stock.available
                or stock.shortfall != 0
                or stock.sellable_bottles < item.quantity_bottles
            ):
                issues.append(
                    self._issue(
                        code="INSUFFICIENT_STOCK",
                        path=f"{path}.quantity_bottles",
                        message=(
                            "Sellable stock is insufficient for the "
                            "recommended quantity."
                        ),
                        correctable=True,
                        product_id=item.product_id,
                    )
                )

            if not self._has_item_issue(
                issues,
                product_id=item.product_id,
            ):
                validated_items.append(
                    ValidatedRecommendationItem(
                        product_id=item.product_id,
                        sku=product.sku,
                        name=product.name,
                        quantity_bottles=item.quantity_bottles,
                        units_per_case=product.units_per_case,
                        cases=(
                            item.quantity_bottles
                            // product.units_per_case
                        ),
                        unit_price_cents=product.price_cents,
                        sellable_bottles=stock.sellable_bottles,
                        certifications=list(product.certifications),
                        rationale=item.rationale,
                    )
                )

        self._append_budget_warning(
            context=context,
            warnings=warnings,
        )

        if issues:
            return RecommendationValidationOutcome(
                valid=False,
                result=None,
                issues=issues,
            )

        result = ValidatedRecommendation(
            items=validated_items,
            total_bottles=total_bottles,
            summary=draft.summary,
            warnings=list(dict.fromkeys(warnings)),
        )
        return RecommendationValidationOutcome(
            valid=True,
            result=result,
            issues=[],
        )

    @staticmethod
    def _products_by_id(
        products: list[ProductRecord],
    ) -> tuple[dict[UUID, ProductRecord], set[UUID]]:
        by_id: dict[UUID, ProductRecord] = {}
        conflicts: set[UUID] = set()
        for product in products:
            product_id = UUID(product.id)
            existing = by_id.get(product_id)
            if existing is not None and existing != product:
                conflicts.add(product_id)
            by_id[product_id] = product
        return by_id, conflicts

    @staticmethod
    def _stock_by_id(
        stock_items: list[StockEvidence],
    ) -> tuple[dict[UUID, StockEvidence], set[UUID]]:
        by_id: dict[UUID, StockEvidence] = {}
        conflicts: set[UUID] = set()
        for item in stock_items:
            existing = by_id.get(item.product_id)
            if existing is not None and existing != item:
                conflicts.add(item.product_id)
            by_id[item.product_id] = item
        return by_id, conflicts

    def _validate_market_and_channel(
        self,
        *,
        product: ProductRecord,
        context: RecommendationContext,
        path: str,
        issues: list[RecommendationValidationIssue],
    ) -> None:
        product_id = UUID(product.id)
        if context.market is not None:
            markets = {
                value.upper()
                for value in product.recommended_markets
            }
            if context.market not in markets:
                issues.append(
                    self._issue(
                        code="MARKET_MISMATCH",
                        path=f"{path}.product_id",
                        message=(
                            "The product is not recommended for the "
                            "requested market."
                        ),
                        correctable=True,
                        product_id=product_id,
                    )
                )

        if context.channel is not None:
            channels = {
                value.casefold()
                for value in product.recommended_channels
            }
            if context.channel not in channels:
                issues.append(
                    self._issue(
                        code="CHANNEL_MISMATCH",
                        path=f"{path}.product_id",
                        message=(
                            "The product is not recommended for the "
                            "requested commercial channel."
                        ),
                        correctable=True,
                        product_id=product_id,
                    )
                )

    def _validate_product_interest(
        self,
        *,
        product: ProductRecord,
        context: RecommendationContext,
        path: str,
        issues: list[RecommendationValidationIssue],
    ) -> None:
        if context.product_interest is None:
            return

        interest = _normalized(context.product_interest)
        searchable = " ".join(
            (
                product.name,
                product.category,
                product.variety,
                product.description,
            )
        )
        if interest not in _normalized(searchable):
            issues.append(
                self._issue(
                    code="PRODUCT_INTEREST_MISMATCH",
                    path=f"{path}.product_id",
                    message=(
                        "Catalog data does not support the requested "
                        "product interest."
                    ),
                    correctable=True,
                    product_id=UUID(product.id),
                )
            )

    def _validate_certifications(
        self,
        *,
        product: ProductRecord,
        context: RecommendationContext,
        path: str,
        issues: list[RecommendationValidationIssue],
    ) -> None:
        if not context.required_certifications:
            return

        product_certifications = {
            _normalized(value)
            for value in product.certifications
        }
        missing = [
            requirement
            for requirement in context.required_certifications
            if _normalized(requirement)
            not in product_certifications
        ]
        if missing:
            issues.append(
                self._issue(
                    code="CERTIFICATION_MISSING",
                    path=f"{path}.product_id",
                    message=(
                        "The selected product lacks one or more "
                        "required certifications."
                    ),
                    correctable=True,
                    product_id=UUID(product.id),
                )
            )

    @staticmethod
    def _append_budget_warning(
        *,
        context: RecommendationContext,
        warnings: list[str],
    ) -> None:
        if context.budget_total_cents is None:
            return
        if (
            context.budget_currency != "EUR"
            or context.estimated_bottles is None
        ):
            warnings.append("BUDGET_NOT_APPLIED")

    @staticmethod
    def _has_item_issue(
        issues: list[RecommendationValidationIssue],
        *,
        product_id: UUID,
    ) -> bool:
        return any(
            issue.product_id == product_id
            for issue in issues
        )

    @staticmethod
    def _issue(
        *,
        code: str,
        path: str,
        message: str,
        correctable: bool,
        product_id: UUID | None = None,
    ) -> RecommendationValidationIssue:
        return RecommendationValidationIssue(
            code=code,
            path=path,
            message=message,
            correctable=correctable,
            product_id=product_id,
        )
