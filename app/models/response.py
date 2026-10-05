from typing import Any

from pydantic import BaseModel, Field
from models.execution_summary import ExecutionTraceSummary


class DataAnalystResponse(BaseModel):

    success: bool

    question: str

    conversation_id: str

    answer: str | None = None

    sql: str | None = None

    result: dict[str, Any] | None = None

    error: str | list[str] | None = None

    needs_clarification: bool = False

    needs_human_approval: bool = False
    human_approval_question: str | None = None
    risk_assessment: dict[str, Any] | None = None

    clarification_question: str | None = None

    clarification_options: list[str] = Field(
        default_factory=list
    )

    execution_trace: list[dict[str, Any]] = Field(
        default_factory=list
    )
    execution_summary: ExecutionTraceSummary | None = None