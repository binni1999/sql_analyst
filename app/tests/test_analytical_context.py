from models.analytical_context import AnalyticalContext


def test_analytical_context_defaults():

    context = AnalyticalContext()

    assert context.entity is None
    assert context.metric is None
    assert context.aggregation is None
    assert context.limit is None
    assert context.sort_direction is None
    assert context.filters == []
    assert context.time_range is None


def test_analytical_context_for_revenue_query():

    context = AnalyticalContext(
        entity="products",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="descending"
    )

    assert context.entity == "products"

    assert context.metric == "revenue"

    assert context.aggregation == "sum"

    assert context.limit == 5

    assert context.sort_direction == "descending"

    assert context.filters == []

    assert context.time_range is None


def test_analytical_context_can_store_filters():

    context = AnalyticalContext(
        entity="products",
        metric="revenue",
        filters=[
            {
                "field": "category",
                "operator": "=",
                "value": "Electronics"
            }
        ]
    )

    assert len(context.filters) == 1

    assert (
        context.filters[0]["field"]
        == "category"
    )

    assert (
        context.filters[0]["operator"]
        == "="
    )

    assert (
        context.filters[0]["value"]
        == "Electronics"
    )


def test_analytical_context_can_store_time_range():

    context = AnalyticalContext(
        entity="products",
        metric="revenue",
        time_range={
            "year": 2025
        }
    )

    assert context.time_range == {
        "year": 2025
    }