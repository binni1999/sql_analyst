from typing import Any

from pydantic import BaseModel, Field


class ExecutionTraceEvent(BaseModel):
    """
    Standardized representation of one execution-trace event.

    The event is validated as a Pydantic model internally and can be
    serialized into the dictionary representation currently used by
    AgentState and existing tests.
    """

    stage: str
    status: str
    attempt: int = 0
    message: str | None = None
    error_type: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)