from pydantic import BaseModel, Field


class ClarificationResult(BaseModel):
    needs_clarification: bool = False

    question: str | None = None

    reason: str | None = None

    options: list[str] = Field(
        default_factory=list
    )