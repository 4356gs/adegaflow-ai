from uuid import UUID

import pytest
from app.agent.tools.catalog import check_stock, get_product_details, search_catalog
from app.agent.tools.customers import retrieve_customer_history
from app.agent.tools.schemas import (
    CheckStockInput,
    ProductDetailsInput,
    RetrieveCustomerHistoryInput,
    SearchCatalogInput,
    StockItemInput,
)
from app.domain.enums import MemoryCategory
from app.repositories.catalog import CatalogRepository
from app.repositories.customers import CustomerRepository
from pydantic import ValidationError
from sqlalchemy.orm import Session

PRODUCT_JOVEN = UUID("11111111-1111-4111-8111-111111111111")
PRODUCT_LIAS = UUID("22222222-2222-4222-8222-222222222222")
UNKNOWN_PRODUCT = UUID("99999999-9999-4999-8999-999999999999")
RHEIN_CUSTOMER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
UNKNOWN_CUSTOMER = UUID("99999999-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def test_search_catalog_returns_ranked_german_albarino(db_session: Session) -> None:
    response = search_catalog(
        SearchCatalogInput(
            query="Albarino",
            market="de",
            channel="specialty_retail",
            limit=2,
        ),
        CatalogRepository(db_session),
    )

    assert response.success is True
    assert response.error is None
    assert response.data is not None
    assert response.data.count == 2
    assert [item.sku for item in response.data.items] == [
        "ADA-ALB-JOV-2025",
        "ADA-ALB-LIA-2024",
    ]
    assert "market_match:DE" in response.data.items[0].match_reasons


def test_search_catalog_applies_price_limit(db_session: Session) -> None:
    response = search_catalog(
        SearchCatalogInput(
            query="Albariño",
            market="DE",
            channel="specialty_retail",
            max_unit_price_cents=1000,
        ),
        CatalogRepository(db_session),
    )

    assert response.data is not None
    assert [item.sku for item in response.data.items] == ["ADA-ALB-JOV-2025"]


def test_get_product_details_excludes_inventory_and_reports_missing(
    db_session: Session,
) -> None:
    response = get_product_details(
        ProductDetailsInput(product_ids=[PRODUCT_JOVEN, UNKNOWN_PRODUCT]),
        CatalogRepository(db_session),
    )

    assert response.success is True
    assert response.data is not None
    assert len(response.data.products) == 1
    assert response.data.products[0].sku == "ADA-ALB-JOV-2025"
    assert response.data.missing_product_ids == [str(UNKNOWN_PRODUCT)]
    assert "available_bottles" not in response.data.products[0].model_dump()


def test_check_stock_reports_documented_shortfall(db_session: Session) -> None:
    response = check_stock(
        CheckStockInput(
            items=[StockItemInput(product_id=PRODUCT_LIAS, requested_bottles=900)]
        ),
        CatalogRepository(db_session),
    )

    assert response.success is True
    assert response.data is not None
    item = response.data.items[0]
    assert item.sellable_bottles == 720
    assert item.available is False
    assert item.shortfall == 180


def test_check_stock_reports_sufficient_stock(db_session: Session) -> None:
    response = check_stock(
        CheckStockInput(
            items=[StockItemInput(product_id=PRODUCT_JOVEN, requested_bottles=600)]
        ),
        CatalogRepository(db_session),
    )

    assert response.data is not None
    assert response.data.items[0].sellable_bottles == 1200
    assert response.data.items[0].available is True
    assert response.data.items[0].shortfall == 0


def test_check_stock_rejects_unknown_product(db_session: Session) -> None:
    response = check_stock(
        CheckStockInput(
            items=[StockItemInput(product_id=UNKNOWN_PRODUCT, requested_bottles=12)]
        ),
        CatalogRepository(db_session),
    )

    assert response.success is False
    assert response.data is None
    assert response.error is not None
    assert response.error.code == "NOT_FOUND"


def test_check_stock_input_rejects_duplicate_products() -> None:
    with pytest.raises(ValidationError):
        CheckStockInput(
            items=[
                StockItemInput(product_id=PRODUCT_JOVEN, requested_bottles=6),
                StockItemInput(product_id=PRODUCT_JOVEN, requested_bottles=12),
            ]
        )


def test_retrieve_customer_history_returns_only_active_memories(
    db_session: Session,
) -> None:
    response = retrieve_customer_history(
        RetrieveCustomerHistoryInput(customer_id=RHEIN_CUSTOMER),
        CustomerRepository(db_session),
    )

    assert response.success is True
    assert response.data is not None
    assert response.data.customer.company_name == "Rhein Selection GmbH"
    assert len(response.data.memories) == 2
    assert all(memory.is_active for memory in response.data.memories)
    assert len(response.data.opportunities) == 1


def test_retrieve_customer_history_filters_memory_category(db_session: Session) -> None:
    response = retrieve_customer_history(
        RetrieveCustomerHistoryInput(
            customer_id=RHEIN_CUSTOMER,
            categories=[MemoryCategory.INTERACTION],
        ),
        CustomerRepository(db_session),
    )

    assert response.data is not None
    assert [memory.category for memory in response.data.memories] == [
        MemoryCategory.INTERACTION
    ]


def test_retrieve_customer_history_returns_not_found(db_session: Session) -> None:
    response = retrieve_customer_history(
        RetrieveCustomerHistoryInput(customer_id=UNKNOWN_CUSTOMER),
        CustomerRepository(db_session),
    )

    assert response.success is False
    assert response.error is not None
    assert response.error.code == "NOT_FOUND"
