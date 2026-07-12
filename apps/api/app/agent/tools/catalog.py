"""Deterministic catalog and stock tools."""

from sqlalchemy.exc import SQLAlchemyError

from app.agent.tools.common import (
    ToolError,
    ToolMeta,
    ToolResponse,
    elapsed_ms,
    started_timer,
)
from app.agent.tools.schemas import (
    CatalogCandidate,
    CheckStockData,
    CheckStockInput,
    ProductDetailsData,
    ProductDetailsInput,
    SearchCatalogData,
    SearchCatalogInput,
    StockItemResult,
)
from app.domain.schemas import ProductRecord
from app.repositories.catalog import CatalogRepository


def search_catalog(
    tool_input: SearchCatalogInput,
    repository: CatalogRepository,
) -> ToolResponse[SearchCatalogData]:
    """Search active products using deterministic filters and ranking."""

    started_ns = started_timer()
    try:
        matches = repository.search(
            query=tool_input.query,
            market=tool_input.market,
            channel=tool_input.channel,
            max_unit_price_cents=tool_input.max_unit_price_cents,
            limit=tool_input.limit,
        )
        items = [
            CatalogCandidate(
                product_id=match.product.id,
                sku=match.product.sku,
                name=match.product.name,
                category=match.product.category,
                price_cents=match.product.price_cents,
                match_reasons=list(match.reasons),
            )
            for match in matches
        ]
        data = SearchCatalogData(items=items, count=len(items))
        return ToolResponse[SearchCatalogData](
            success=True,
            data=data,
            error=None,
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
    except SQLAlchemyError:
        return ToolResponse[SearchCatalogData](
            success=False,
            data=None,
            error=ToolError(
                code="PERSISTENCE_ERROR",
                message="Catalog data could not be read.",
                retryable=True,
            ),
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )


def get_product_details(
    tool_input: ProductDetailsInput,
    repository: CatalogRepository,
) -> ToolResponse[ProductDetailsData]:
    """Return complete product records without inventory fields."""

    started_ns = started_timer()
    try:
        product_ids = [str(product_id) for product_id in tool_input.product_ids]
        products, missing = repository.get_products(product_ids)
        data = ProductDetailsData(
            products=[ProductRecord.model_validate(product) for product in products],
            missing_product_ids=missing,
        )
        return ToolResponse[ProductDetailsData](
            success=True,
            data=data,
            error=None,
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
    except SQLAlchemyError:
        return ToolResponse[ProductDetailsData](
            success=False,
            data=None,
            error=ToolError(
                code="PERSISTENCE_ERROR",
                message="Product details could not be read.",
                retryable=True,
            ),
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )


def check_stock(
    tool_input: CheckStockInput,
    repository: CatalogRepository,
) -> ToolResponse[CheckStockData]:
    """Check sellable stock without reserving or mutating inventory."""

    started_ns = started_timer()
    try:
        requested_by_id = {
            str(item.product_id): item.requested_bottles for item in tool_input.items
        }
        snapshots, missing = repository.get_stock(list(requested_by_id))
        if missing:
            return ToolResponse[CheckStockData](
                success=False,
                data=None,
                error=ToolError(
                    code="NOT_FOUND",
                    message="One or more products do not exist or are inactive.",
                    retryable=False,
                ),
                meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
            )

        items: list[StockItemResult] = []
        by_id = {snapshot.product_id: snapshot for snapshot in snapshots}
        for product_id in requested_by_id:
            requested = requested_by_id[product_id]
            sellable = by_id[product_id].sellable_bottles
            items.append(
                StockItemResult(
                    product_id=product_id,
                    requested_bottles=requested,
                    sellable_bottles=sellable,
                    available=sellable >= requested,
                    shortfall=max(0, requested - sellable),
                )
            )

        return ToolResponse[CheckStockData](
            success=True,
            data=CheckStockData(items=items),
            error=None,
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
    except SQLAlchemyError:
        return ToolResponse[CheckStockData](
            success=False,
            data=None,
            error=ToolError(
                code="PERSISTENCE_ERROR",
                message="Inventory data could not be read.",
                retryable=True,
            ),
            meta=ToolMeta(duration_ms=elapsed_ms(started_ns)),
        )
