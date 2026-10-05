from models.analytical_context import AnalyticalContext
from validation.sql_requirements import SQLRequirementsBuilder


def test_build_empty_requirements_without_context():
    builder = SQLRequirementsBuilder()

    result = builder.build(None)

    assert result.metric is None
    assert result.aggregation is None
    assert result.entity is None
    assert result.group_by_required is False
    assert result.filters == []
    assert result.time_range is None
    assert result.time_range_required is False
    assert result.sort_direction is None
    assert result.limit is None


def test_build_revenue_product_requirements():
    builder = SQLRequirementsBuilder()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    result = builder.build(context)

    assert result.metric == "revenue"
    assert result.aggregation == "sum"
    assert result.entity == "product"
    assert result.group_by_required is True
    assert result.limit == 5
    assert result.sort_direction == "desc"


def test_build_time_range_requirement():
    builder = SQLRequirementsBuilder()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        time_range={
            "type": "year",
            "year": 2025,
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
    )

    result = builder.build(context)

    assert result.time_range_required is True
    assert result.time_range == {
        "type": "year",
        "year": 2025,
        "start": "2025-01-01",
        "end": "2025-12-31",
    }


def test_build_filters_without_mutating_context():
    builder = SQLRequirementsBuilder()

    filters = [
        {
            "field": "city",
            "operator": "=",
            "value": "Delhi",
        }
    ]

    context = AnalyticalContext(
        entity="customer",
        metric="revenue",
        aggregation="sum",
        filters=filters,
    )

    result = builder.build(context)

    assert result.filters == filters

    # Ensure the builder created a separate list.
    assert result.filters is not context.filters


def test_build_bottom_products_requirements():
    builder = SQLRequirementsBuilder()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=10,
        sort_direction="asc",
    )

    result = builder.build(context)

    assert result.entity == "product"
    assert result.metric == "revenue"
    assert result.aggregation == "sum"
    assert result.group_by_required is True
    assert result.limit == 10
    assert result.sort_direction == "asc"