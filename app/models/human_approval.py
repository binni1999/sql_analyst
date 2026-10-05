from enum import Enum

from pydantic import BaseModel, Field


class HumanApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskAssessment(BaseModel):
    is_risky: bool = False
    risk_level: str = "low"
    reasons: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)

    @property
    def requires_approval(self) -> bool:
        return self.is_risky
