"""Persistence operations for atomic internal actions and receipts."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CustomerMemory,
    FollowUpTask,
    InternalActionReceipt,
    Opportunity,
)
from app.domain.enums import InternalActionName


class InternalActionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_receipt(self, idempotency_key: str) -> InternalActionReceipt | None:
        return self._session.scalar(
            select(InternalActionReceipt).where(
                InternalActionReceipt.idempotency_key == idempotency_key
            )
        )

    def add_receipt(
        self,
        *,
        agent_run_id: str,
        action_name: InternalActionName,
        idempotency_key: str,
        fingerprint: str,
        result_payload: Mapping[str, object],
    ) -> InternalActionReceipt:
        receipt = InternalActionReceipt(
            id=str(uuid4()),
            agent_run_id=agent_run_id,
            action_name=action_name.value,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            result_payload=dict(result_payload),
        )
        self._session.add(receipt)
        self._session.flush()
        return receipt

    def get_opportunity_for_inquiry(self, inquiry_id: str) -> Opportunity | None:
        return self._session.scalar(select(Opportunity).where(Opportunity.inquiry_id == inquiry_id))

    def add_opportunity(self, **values: object) -> Opportunity:
        opportunity = Opportunity(id=str(uuid4()), **values)
        self._session.add(opportunity)
        self._session.flush()
        return opportunity

    def add_followup(self, **values: object) -> FollowUpTask:
        followup = FollowUpTask(id=str(uuid4()), **values)
        self._session.add(followup)
        self._session.flush()
        return followup

    def find_memory(
        self,
        *,
        customer_id: str,
        category: str,
        normalized_content: str,
        source_inquiry_id: str,
    ) -> CustomerMemory | None:
        candidates = self._session.scalars(
            select(CustomerMemory).where(
                CustomerMemory.customer_id == customer_id,
                CustomerMemory.category == category,
                CustomerMemory.source_inquiry_id == source_inquiry_id,
                CustomerMemory.is_active.is_(True),
            )
        )
        key = normalized_content.casefold()
        return next(
            (item for item in candidates if " ".join(item.content.split()).casefold() == key),
            None,
        )

    def add_memory(self, **values: object) -> CustomerMemory:
        memory = CustomerMemory(id=str(uuid4()), **values)
        self._session.add(memory)
        self._session.flush()
        return memory
