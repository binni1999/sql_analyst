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


def test_explicit_new_question_is_not_classified_as_follow_up():
    resolver = FollowUpResolver()

    assert resolver.is_follow_up("What about quantity?") is True
    assert resolver.is_follow_up("Show revenue by customer") is False
    assert resolver.is_follow_up("How many orders were placed in 2025?") is False


def test_resolver_does_not_merge_unrelated_question():
    resolver = FollowUpResolver()
    conversation = create_conversation("Show the top 5 products by revenue")

    try:
        resolver.resolve(conversation, "Show revenue by customer")
    except ValueError as exc:
        assert "not a contextual follow-up" in str(exc)
    else:
        raise AssertionError("Expected unrelated question to remain independent")



def test_top_n_follow_up_replaces_existing_limit():
    resolver = FollowUpResolver()
    conversation = create_conversation("Show the top 5 products by revenue")
    assert resolver.resolve(conversation, "top 3") == "Show the top 3 products by revenue"


def test_show_only_top_n_is_recognized_as_limit_follow_up():
    resolver = FollowUpResolver()
    conversation = create_conversation("Show the top 5 products by revenue")
    assert resolver.is_follow_up("Show only the top 3") is True
    assert resolver.resolve(conversation, "Show only the top 3") == "Show the top 3 products by revenue"


def test_discount_metric_follow_up_replaces_revenue():
    resolver = FollowUpResolver()
    conversation = create_conversation("Show the top 5 products by revenue")
    assert resolver.resolve(conversation, "What about total discount amount?") == (
        "Show the top 5 products by discount amount"
    )
