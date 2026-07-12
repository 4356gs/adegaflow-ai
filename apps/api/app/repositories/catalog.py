"""Repository queries for products and inventory."""

from dataclasses import dataclass
from unicodedata import combining, normalize

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Inventory, Product


@dataclass(frozen=True, slots=True)
class CatalogMatch:
    product: Product
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StockSnapshot:
    product_id: str
    available_bottles: int
    reserved_bottles: int

    @property
    def sellable_bottles(self) -> int:
        return max(0, self.available_bottles - self.reserved_bottles)


def _normalized(value: str) -> str:
    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


class CatalogRepository:
    """Read-only product and stock access for deterministic tools."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self,
        *,
        query: str,
        market: str | None,
        channel: str | None,
        max_unit_price_cents: int | None,
        limit: int,
    ) -> list[CatalogMatch]:
        statement = select(Product).where(Product.active.is_(True))
        if max_unit_price_cents is not None:
            statement = statement.where(Product.price_cents <= max_unit_price_cents)

        products = self._session.scalars(statement).all()
        query_normalized = _normalized(query.strip())
        market_normalized = market.upper() if market else None
        channel_normalized = channel.casefold() if channel else None
        matches: list[CatalogMatch] = []

        for product in products:
            recommended_markets = {value.upper() for value in product.recommended_markets}
            recommended_channels = {value.casefold() for value in product.recommended_channels}
            if market_normalized and market_normalized not in recommended_markets:
                continue
            if channel_normalized and channel_normalized not in recommended_channels:
                continue

            reasons: list[str] = []
            score = 0
            searchable_fields = (
                ("sku", product.sku, 60),
                ("name", product.name, 50),
                ("variety", product.variety, 40),
                ("category", product.category, 30),
                ("description", product.description, 15),
            )
            for label, value, weight in searchable_fields:
                if query_normalized in _normalized(value):
                    reasons.append(f"query_match:{label}")
                    score += weight

            if not reasons:
                continue
            if market_normalized:
                reasons.append(f"market_match:{market_normalized}")
                score += 20
            if channel_normalized:
                reasons.append(f"channel_match:{channel_normalized}")
                score += 20

            matches.append(CatalogMatch(product=product, score=score, reasons=tuple(reasons)))

        matches.sort(key=lambda match: (-match.score, match.product.price_cents, match.product.sku))
        return matches[:limit]

    def get_products(self, product_ids: list[str]) -> tuple[list[Product], list[str]]:
        if not product_ids:
            return [], []

        products = self._session.scalars(
            select(Product).where(Product.id.in_(product_ids), Product.active.is_(True))
        ).all()
        by_id = {product.id: product for product in products}
        found = [by_id[product_id] for product_id in product_ids if product_id in by_id]
        missing = [product_id for product_id in product_ids if product_id not in by_id]
        return found, missing

    def get_stock(self, product_ids: list[str]) -> tuple[list[StockSnapshot], list[str]]:
        if not product_ids:
            return [], []

        rows = self._session.execute(
            select(
                Product.id,
                Inventory.available_bottles,
                Inventory.reserved_bottles,
            )
            .join(Inventory, Inventory.product_id == Product.id)
            .where(Product.id.in_(product_ids), Product.active.is_(True))
        ).all()
        by_id = {
            product_id: StockSnapshot(
                product_id=product_id,
                available_bottles=available_bottles,
                reserved_bottles=reserved_bottles,
            )
            for product_id, available_bottles, reserved_bottles in rows
        }
        found = [by_id[product_id] for product_id in product_ids if product_id in by_id]
        missing = [product_id for product_id in product_ids if product_id not in by_id]
        return found, missing
