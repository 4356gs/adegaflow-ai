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


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class AgentRunStep(StrEnum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    RETRIEVING_MEMORY = "retrieving_memory"
    SELECTING_PRODUCTS = "selecting_products"
    CHECKING_STOCK = "checking_stock"
    VALIDATING_RECOMMENDATION = "validating_recommendation"
    CALCULATING_QUOTE = "calculating_quote"
    GENERATING_ARTIFACTS = "generating_artifacts"
    PERSISTING_ACTIONS = "persisting_actions"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ToolExecutionStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"


class ArtifactType(StrEnum):
    PROPOSAL = "proposal"
    EMAIL_DRAFT = "email_draft"


class ReviewStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"


class FollowUpStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class InternalActionName(StrEnum):
    CREATE_CRM_OPPORTUNITY = "create_crm_opportunity"
    CREATE_FOLLOWUP_TASK = "create_followup_task"
    SAVE_CUSTOMER_MEMORY = "save_customer_memory"
