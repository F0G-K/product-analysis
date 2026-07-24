from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    ASSESSMENT = "assessment"
    CONSISTENCY_CHECK = "consistency_check"
    ATTRIBUTION = "attribution"


class TaskStatus(StrEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {self.COMPLETED, self.CANCELLED}


class ProjectRole(StrEnum):
    PROJECT_ADMIN = "project_admin"
    PROJECT_MEMBER = "project_member"
    VIEWER = "viewer"


class ReviewOperation(StrEnum):
    CONFIRMED = "confirmed"
    REVISED = "revised"
    REJECTED = "rejected"


class EvidenceType(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    MISSING = "missing"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AIRoleName(StrEnum):
    INPUT_VALIDATOR = "input_validator"
    SNAPSHOT_LOCKER = "snapshot_locker"
    DOCUMENT_RETRIEVER = "document_retriever"
    RULE_ANALYST = "rule_analyst"
    LLM_ANALYST = "llm_analyst"
    EVIDENCE_LINKER = "evidence_linker"
    CONFIDENCE_ASSESSOR = "confidence_assessor"
    HUMAN_REVIEW_COORDINATOR = "human_review_coordinator"
    RESULT_FINALIZER = "result_finalizer"

