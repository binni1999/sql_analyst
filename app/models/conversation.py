from typing import Any

from pydantic import BaseModel, Field

from models.clarification import ClarificationResult
from models.analytical_context import AnalyticalContext
from models.memory import ConversationMemory


class ConversationState(BaseModel):

    conversation_id: str

    original_question: str | None = None

    clarification: ClarificationResult | None = None

    resolved_question: str | None = None

    analytical_context: AnalyticalContext | None = None

    # Explicit structured memory for the conversation.
    #
    # Existing fields above remain for backward compatibility and for
    # callers/tests that directly inspect ConversationState.
    memory: ConversationMemory = Field(
        default_factory=ConversationMemory
    )

    waiting_for_clarification: bool = False

    waiting_for_human_approval: bool = False
    pending_agent_state: dict[str, Any] | None = None

    history: list[dict[str, str]] = Field(
        default_factory=list
    )
