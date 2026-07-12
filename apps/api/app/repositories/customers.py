"""Repository queries for customer history and explicit memory."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Customer, CustomerMemory, Opportunity
from app.domain.enums import MemoryCategory


class CustomerRepository:
    """Read-only customer history access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, customer_id: str) -> Customer | None:
        return self._session.get(Customer, customer_id)

    def list_active_memories(
        self,
        *,
        customer_id: str,
        categories: list[MemoryCategory] | None,
        limit: int,
    ) -> list[CustomerMemory]:
        statement = (
            select(CustomerMemory)
            .where(
                CustomerMemory.customer_id == customer_id,
                CustomerMemory.is_active.is_(True),
            )
            .order_by(CustomerMemory.created_at.desc(), CustomerMemory.id)
            .limit(limit)
        )
        if categories:
            statement = statement.where(
                CustomerMemory.category.in_([category.value for category in categories])
            )
        return list(self._session.scalars(statement).all())

    def list_opportunities(self, *, customer_id: str, limit: int) -> list[Opportunity]:
        statement = (
            select(Opportunity)
            .where(Opportunity.customer_id == customer_id)
            .order_by(Opportunity.created_at.desc(), Opportunity.id)
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())
