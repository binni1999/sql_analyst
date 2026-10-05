from typing import Any

from pydantic import BaseModel, Field

from models.analytical_context import AnalyticalContext
from models.intent import QuestionIntent


class EvaluationTurn(BaseModel):
    """One user turn in an evaluation conversation."""

    question: str
    expected_resolved_question: str | None = None
    expected_analytical_context: AnalyticalContext | None = None


class EvaluationCase(BaseModel):
    """Ground-truth contract for one evaluation scenario.

    The dataset deliberately separates expected SQL, semantic expectations,
    result expectations, and agent behavior so later evaluators can score each
    dimension independently.
    """

    case_id: str
    category: str
    description: str

    question: str
    conversation: list[EvaluationTurn] = Field(default_factory=list)

    expected_intent: QuestionIntent | None = None
    expected_resolved_question: str | None = None
    expected_analytical_context: AnalyticalContext | None = None

    expected_sql: str | None = None
    expected_tables: list[str] = Field(default_factory=list)
    expected_metric: str | None = None

    # Result expectations are structural/semantic rather than fabricated row
    # values. Exact values can be populated later from a fixed DB snapshot.
    expected_result: dict[str, Any] | None = None

    # Human-readable answer contract. Exact wording is intentionally avoided.
    expected_answer: str | None = None

    # Expectations used by the agent-behavior evaluators added later.
    expected_behavior: dict[str, Any] = Field(default_factory=dict)

    expected_business_knowledge_documents: list[str] = Field(
        default_factory=list
    )
    expected_tools: list[str] = Field(default_factory=list)
    expected_route: list[str] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)


class EvaluationDataset(BaseModel):
    """A versioned collection of evaluation cases."""

    dataset_id: str
    version: str
    description: str
    cases: list[EvaluationCase]
