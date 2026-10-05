from agents.follow_up_resolver import FollowUpResolver
from models.conversation import ConversationState


def create_conversation(
    question: str
) -> ConversationState:

    return ConversationState(
        conversation_id="test-1",
        original_question=question,
        resolved_question=question,
        history=[
            {
                "role": "user",
                "content": question
            },
            {
                "role": "assistant",
                "content": "Previous answer"
            }
        ]
    )


def test_metric_follow_up_revenue_to_quantity():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show the top 5 products by revenue"
    )

    result = resolver.resolve(
        conversation,
        "What about quantity?"
    )

    assert (
        result
        == "Show the top 5 products by quantity"
    )


def test_metric_follow_up_revenue_to_units():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show the top 5 products by revenue"
    )

    result = resolver.resolve(
        conversation,
        "What about units?"
    )

    assert (
        result
        == "Show the top 5 products by quantity"
    )


def test_sort_ascending():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show revenue by product"
    )

    result = resolver.resolve(
        conversation,
        "Sort ascending"
    )

    assert (
        result
        == (
            "Show revenue by product "
            "sorted in ascending order"
        )
    )


def test_sort_descending():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show revenue by product"
    )

    result = resolver.resolve(
        conversation,
        "Highest first"
    )

    assert (
        result
        == (
            "Show revenue by product "
            "sorted in descending order"
        )
    )


def test_filter_follow_up():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show revenue by product"
    )

    result = resolver.resolve(
        conversation,
        "Only for 2025"
    )

    assert (
        result
        == (
            "Show revenue by product "
            "with only for 2025"
        )
    )


def test_generic_follow_up():

    resolver = FollowUpResolver()

    conversation = create_conversation(
        "Show revenue by product"
    )

    result = resolver.resolve(
        conversation,
        "Include product names"
    )

    assert (
        result
        == (
            "Show revenue by product. "
            "Include product names"
        )
    )


def test_no_previous_context():

    resolver = FollowUpResolver()

    conversation = ConversationState(
        conversation_id="test-1"
    )

    try:

        resolver.resolve(
            conversation,
            "What about quantity?"
        )

        assert False

    except ValueError as exc:

        assert (
            "No previous question"
            in str(exc)
        )