from models.analytical_context import AnalyticalContext
from models.conversation import ConversationState


def test_conversation_state_stores_analytical_context():

    context = AnalyticalContext(
        entity="products",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="descending"
    )

    conversation = ConversationState(
        conversation_id="test-1",
        analytical_context=context
    )

    assert conversation.analytical_context is not None

    assert (
        conversation.analytical_context.entity
        == "products"
    )

    assert (
        conversation.analytical_context.metric
        == "revenue"
    )

    assert (
        conversation.analytical_context.limit
        == 5
    )

    assert (
        conversation.analytical_context.sort_direction
        == "descending"
    )