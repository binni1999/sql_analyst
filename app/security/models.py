from pydantic import BaseModel, Field


class GuardrailViolation(BaseModel):
    """A single security-policy violation detected for a SQL statement."""

    rule: str
    message: str
    severity: str = "error"


class GuardrailResult(BaseModel):
    """Structured result returned by the SQL security boundary."""

    allowed: bool
    violations: list[GuardrailViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_sql: str | None = None
