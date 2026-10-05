from factory import create_data_analyst_service
from models.request import DataAnalystRequest


def test_two_turn_conversation_follow_up():

    service = create_data_analyst_service()

    # -----------------------------------------
    # Turn 1
    # -----------------------------------------

    response_1 = service.ask(
        DataAnalystRequest(
            question="Show the top 5 products by revenue"
        )
    )

    assert response_1.success is True

    assert response_1.conversation_id

    assert response_1.answer is not None

    assert response_1.sql is not None

    conversation_id = (
        response_1.conversation_id
    )

    # -----------------------------------------
    # Turn 2
    # -----------------------------------------

    response_2 = service.ask(
        DataAnalystRequest(
            question="What about quantity?",
            conversation_id=conversation_id
        )
    )

    assert response_2.success is True

    assert (
        response_2.conversation_id
        == conversation_id
    )

    assert response_2.answer is not None

    assert response_2.sql is not None

    # -----------------------------------------
    # Conversation state
    # -----------------------------------------

    conversation = (
        service.conversation_service.get(
            conversation_id
        )
    )

    assert conversation is not None

    assert (
        conversation.resolved_question
        == "Show the top 5 products by quantity"
    )

    # -----------------------------------------
    # Conversation history
    # -----------------------------------------

    assert len(conversation.history) == 4

    assert conversation.history[0] == {
        "role": "user",
        "content": (
            "Show the top 5 products by revenue"
        )
    }

    assert (
        conversation.history[1]["role"]
        == "assistant"
    )

    assert (
        conversation.history[2] == {
            "role": "user",
            "content": "What about quantity?"
        }
    )

    assert (
        conversation.history[3]["role"]
        == "assistant"
    )