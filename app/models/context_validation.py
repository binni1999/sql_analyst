from pydantic import BaseModel, Field


class ContextValidationResult(BaseModel):
    """
    Result of validating generated SQL against
    deterministic analytical requirements.
    """

    is_valid: bool

    errors: list[str] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)