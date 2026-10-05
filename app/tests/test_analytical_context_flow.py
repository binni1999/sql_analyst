from factory import create_data_analyst_service
from models.request import DataAnalystRequest


def test_analytical_context_evolves_across_conversation():
    service = create_data_analyst_service()

    
    # --------------------------------------------------
    # Turn 1
    # --------------------------------------------------

    first_request = DataAnalystRequest(
        question="Show the top 5 products by revenue"
    )

    first_response = service.ask(first_request)

    assert first_response.success is True
    assert first_response.conversation_id

    conversation_id = first_response.conversation_id

    # Retrieve the conversation state
    conversation = (
        service.conversation_service.get(
            conversation_id
        )
    )

    assert conversation is not None
    assert conversation.analytical_context is not None

    context = conversation.analytical_context

    # Verify Turn 1 context
    assert context.entity == "product"
    assert context.metric == "revenue"
    assert context.aggregation == "sum"
    assert context.limit == 5
    assert context.sort_direction == "descending"

    # --------------------------------------------------
    # Turn 2
    # --------------------------------------------------

    second_request = DataAnalystRequest(
        question="What about quantity?",
        conversation_id=conversation_id
    )

    second_response = service.ask(second_request)

    assert second_response.success is True
    assert second_response.conversation_id == conversation_id

    # Retrieve updated conversation state
    conversation = (
        service.conversation_service.get(
            conversation_id
        )
    )

    assert conversation is not None
    assert conversation.analytical_context is not None

    context = conversation.analytical_context

    # --------------------------------------------------
    # Verify context evolution
    # --------------------------------------------------

    # Entity should be preserved
    assert context.entity == "product"

    # Metric should change
    assert context.metric == "quantity"

    # Aggregation should remain SUM
    assert context.aggregation == "sum"

    # Limit should be preserved from Turn 1
    assert context.limit == 5

    # Sort direction should be preserved
    assert context.sort_direction == "descending"

    # Follow-up should resolve to the expected question
    assert (
        conversation.resolved_question
        == "Show the top 5 products by quantity"
    )