from models.conversation import ConversationState
from services.conversation_service import ConversationService


def test_create_conversation():

    service = ConversationService()

    conversation = service.create(
        "test-conversation"
    )

    assert isinstance(
        conversation,
        ConversationState
    )

    assert (
        conversation.conversation_id
        == "test-conversation"
    )

    assert conversation.history == []


def test_get_or_create_returns_same_conversation():

    service = ConversationService()

    first = service.get_or_create(
        "conversation-1"
    )

    second = service.get_or_create(
        "conversation-1"
    )

    assert first is second


def test_add_message():

    service = ConversationService()

    service.create(
        "conversation-1"
    )

    conversation = service.add_message(
        conversation_id="conversation-1",
        role="user",
        content="Show top products"
    )

    assert len(conversation.history) == 1

    assert conversation.history[0] == {
        "role": "user",
        "content": "Show top products"
    }


def test_add_multiple_messages():

    service = ConversationService()

    service.add_message(
        conversation_id="conversation-1",
        role="user",
        content="Show top products"
    )

    service.add_message(
        conversation_id="conversation-1",
        role="assistant",
        content="Here are the top products."
    )

    conversation = service.get(
        "conversation-1"
    )

    assert conversation is not None

    assert len(conversation.history) == 2

    assert conversation.history[0]["role"] == "user"

    assert (
        conversation.history[1]["role"]
        == "assistant"
    )


def test_delete_conversation():

    service = ConversationService()

    service.create(
        "conversation-1"
    )

    service.delete(
        "conversation-1"
    )

    assert (
        service.get("conversation-1")
        is None
    )