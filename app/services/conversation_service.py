from models.conversation import ConversationState


class ConversationService:

    def __init__(self):
        self._conversations: dict[
            str,
            ConversationState
        ] = {}

    def create(
        self,
        conversation_id: str
    ) -> ConversationState:

        state = ConversationState(
            conversation_id=conversation_id
        )

        self._conversations[
            conversation_id
        ] = state

        return state

    def get(
        self,
        conversation_id: str
    ) -> ConversationState | None:

        return self._conversations.get(
            conversation_id
        )

    def get_or_create(
        self,
        conversation_id: str
    ) -> ConversationState:

        existing = self.get(
            conversation_id
        )

        if existing:
            return existing

        return self.create(
            conversation_id
        )

    def save(
        self,
        state: ConversationState
    ) -> ConversationState:

        self._conversations[
            state.conversation_id
        ] = state

        return state

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> ConversationState:

        conversation = self.get_or_create(
            conversation_id
        )

        conversation.history.append(
            {
                "role": role,
                "content": content
            }
        )

        return self.save(conversation)

    def delete(
        self,
        conversation_id: str
    ) -> None:

        self._conversations.pop(
            conversation_id,
            None
        )