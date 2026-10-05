from models.analytical_context import AnalyticalContext
from models.conversation import ConversationState


class ConversationMemoryService:
    """Manage structured memory for a single ConversationState.

    This milestone keeps memory conversation-scoped and in-process.
    Persistence across application restarts remains a separate concern
    from LangGraph checkpoint persistence.
    """

    MAX_RECENT_TURNS = 5

    def remember_turn(
        self,
        conversation: ConversationState,
        *,
        user_question: str,
        resolved_question: str,
        analytical_context: AnalyticalContext | None,
        answer: str | None,
    ) -> ConversationState:
        memory = conversation.memory

        memory.recent_questions.append(
            user_question
        )
        memory.recent_resolved_questions.append(
            resolved_question
        )

        memory.recent_questions = (
            memory.recent_questions[
                -self.MAX_RECENT_TURNS:
            ]
        )
        memory.recent_resolved_questions = (
            memory.recent_resolved_questions[
                -self.MAX_RECENT_TURNS:
            ]
        )

        memory.last_answer = answer

        if analytical_context is not None:
            memory.analytical_context = (
                analytical_context.model_copy(
                    deep=True
                )
            )

        memory.turn_count += 1

        # Keep the legacy ConversationState fields synchronized.
        conversation.resolved_question = (
            resolved_question
        )

        if analytical_context is not None:
            conversation.analytical_context = (
                analytical_context.model_copy(
                    deep=True
                )
            )

        return conversation

    def get_last_resolved_question(
        self,
        conversation: ConversationState,
    ) -> str | None:
        return (
            conversation.memory
            .recent_resolved_questions[-1]
            if conversation.memory.recent_resolved_questions
            else None
        )

    def get_analytical_context(
        self,
        conversation: ConversationState,
    ) -> AnalyticalContext | None:
        if conversation.memory.analytical_context is None:
            return None

        return conversation.memory.analytical_context.model_copy(
            deep=True
        )
