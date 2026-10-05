from pydantic import BaseModel, Field

from models.analytical_context import AnalyticalContext


class ConversationMemory(BaseModel):
    """Structured memory for a single analytical conversation.

    The memory is intentionally conversation-scoped. It separates:
    - short-term memory: recent user/resolved questions and last answer
    - analytical memory: the latest structured AnalyticalContext

    Long-term cross-user preferences are deliberately out of scope for
    this milestone because the current application has no user identity
    or preference store.
    """

    recent_questions: list[str] = Field(default_factory=list)
    recent_resolved_questions: list[str] = Field(default_factory=list)

    last_answer: str | None = None

    analytical_context: AnalyticalContext | None = None

    turn_count: int = 0
