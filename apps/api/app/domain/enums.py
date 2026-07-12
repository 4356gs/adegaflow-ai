"""Domain enumerations shared by persistence and tool contracts."""

from enum import StrEnum


class MemoryCategory(StrEnum):
    PREFERENCE = "preference"
    REQUIREMENT = "requirement"
    INTERACTION = "interaction"
    CONSTRAINT = "constraint"


class InquirySource(StrEnum):
    MANUAL = "manual"
    DEMO = "demo"
    EMAIL_SIMULATED = "email_simulated"


class InquiryStatus(StrEnum):
    NEW = "new"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OpportunityStage(StrEnum):
    QUALIFIED = "qualified"
    PROPOSAL_DRAFT = "proposal_draft"
    FOLLOW_UP = "follow_up"


class OpportunityPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
