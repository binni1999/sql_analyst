from enum import Enum

from pydantic import BaseModel, Field

from models.agent import (
    MetadataResult,
    SQLResult,
    AnalyticsResult
)
from models.intent import QuestionIntent
from models.clarification import ClarificationResult
from models.analytical_context import AnalyticalContext
from models.business_knowledge import BusinessKnowledgeResult
from models.human_approval import HumanApprovalStatus, RiskAssessment


class AgentStep(str, Enum):
    INITIALIZED = "initialized"
    METADATA = "metadata"
    SQL = "sql"
    ANALYTICS = "analytics"
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    HUMAN_APPROVAL = "human_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(BaseModel):
    question: str
    resolved_question: str | None = None

    analytical_context: AnalyticalContext | None = None

    intent: QuestionIntent = QuestionIntent.UNKNOWN

    clarification: ClarificationResult | None = None

    metadata: MetadataResult | None = None

    business_knowledge: BusinessKnowledgeResult | None = None

    sql: SQLResult | None = None

    analytics: AnalyticsResult | None = None

    answer: str | None = None

    execution_trace: list[dict[str, object]] = Field(
        default_factory=list
    )

    current_step: AgentStep = AgentStep.INITIALIZED

    success: bool = False

    error: str | list[str] | None = None

    human_approval_required: bool = False
    human_approval_status: HumanApprovalStatus = HumanApprovalStatus.NOT_REQUIRED
    human_approval_question: str | None = None
    risk_assessment: RiskAssessment | None = None

    def mark_success(self):
        self.success = True
        self.error = None
        return self

    def mark_failure(self, error):
        self.success = False
        self.error = error
        self.current_step = AgentStep.FAILED
        return self