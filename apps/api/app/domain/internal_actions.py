"""Strict contracts for deterministic internal commercial actions."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import (
    FollowUpStatus,
    InternalActionName,
    MemoryCategory,
    OpportunityPriority,
    OpportunityStage,
)


class StrictActionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OpportunityActionInput(StrictActionModel):
    inquiry_id: UUID
    customer_id: UUID
    title: str = Field(min_length=1, max_length=200)
    stage: Literal[OpportunityStage.PROPOSAL_DRAFT] = OpportunityStage.PROPOSAL_DRAFT
    priority: OpportunityPriority
    score: int = Field(ge=0, le=100)
    market: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    channel: str | None = Field(default=None, max_length=80)
    estimated_bottles: int | None = Field(default=None, gt=0)
    target_date: date | None = None
    summary: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def priority_matches_score(self) -> OpportunityActionInput:
        expected = priority_for_score(self.score)
        if self.priority is not expected:
            raise ValueError("priority must be derived from score")
        return self


class FollowUpActionInput(StrictActionModel):
    opportunity_id: UUID
    title: str = Field(min_length=1, max_length=200)
    due_at: datetime
    status: Literal[FollowUpStatus.PENDING] = FollowUpStatus.PENDING
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must be timezone-aware")
        return value


class MemoryFactInput(StrictActionModel):
    category: Literal[
        MemoryCategory.PREFERENCE,
        MemoryCategory.REQUIREMENT,
        MemoryCategory.INTERACTION,
    ]
    content: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1.0, ge=1.0, le=1.0)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return " ".join(value.split())


class MemoryActionInput(StrictActionModel):
    customer_id: UUID
    source_inquiry_id: UUID
    memories: list[MemoryFactInput] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("memories")
    @classmethod
    def normalize_and_sort_memories(cls, values: list[MemoryFactInput]) -> list[MemoryFactInput]:
        deduplicated: dict[tuple[str, str], MemoryFactInput] = {}
        for value in values:
            key = (str(value.category), value.content.casefold())
            deduplicated.setdefault(key, value)
        return sorted(
            deduplicated.values(),
            key=lambda item: (str(item.category), item.content.casefold()),
        )


class CustomerActionReference(StrictActionModel):
    customer_id: UUID
    created: bool


class OpportunityActionReference(StrictActionModel):
    opportunity_id: UUID
    stage: OpportunityStage
    priority: OpportunityPriority
    score: int = Field(ge=0, le=100)


class FollowUpActionReference(StrictActionModel):
    followup_task_id: UUID
    due_at: datetime
    status: FollowUpStatus


class MemoryActionReference(StrictActionModel):
    saved_count: int = Field(ge=0, le=20)
    memory_ids: list[UUID] = Field(max_length=20)
    warning: str | None = None


class InternalActionsResult(StrictActionModel):
    customer: CustomerActionReference
    opportunity: OpportunityActionReference
    followup: FollowUpActionReference
    memory: MemoryActionReference


class InternalActionEnvelope(StrictActionModel):
    action_name: InternalActionName
    reused: bool
    fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    result: dict[str, object]


def priority_for_score(score: int) -> OpportunityPriority:
    if score < 50:
        return OpportunityPriority.LOW
    if score < 75:
        return OpportunityPriority.MEDIUM
    return OpportunityPriority.HIGH


def canonical_fingerprint(payload: BaseModel) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
