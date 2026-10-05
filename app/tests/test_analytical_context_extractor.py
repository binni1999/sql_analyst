from datetime import date

from agents.analytical_context_extractor import (
    AnalyticalContextExtractor
)
from models.analytical_context import AnalyticalContext


def create_extractor():
    return AnalyticalContextExtractor()


# ============================================================
# ENTITY
# ============================================================

def test_extract_product_entity():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by revenue"
    )

    assert context.entity == "product"


# ============================================================
# METRIC
# ============================================================

def test_extract_revenue_metric():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by revenue"
    )

    assert context.metric == "revenue"


def test_extract_quantity_metric():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by quantity"
    )

    assert context.metric == "quantity"


# ============================================================
# AGGREGATION
# ============================================================

def test_revenue_defaults_to_sum():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by revenue"
    )

    assert context.aggregation == "sum"


def test_rating_defaults_to_average():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by rating"
    )

    assert context.aggregation == "avg"


def test_explicit_average():

    extractor = create_extractor()

    context = extractor.extract(
        "Show average product rating"
    )

    assert context.aggregation == "avg"


# ============================================================
# LIMIT + SORT
# ============================================================

def test_extract_top_limit():

    extractor = create_extractor()

    context = extractor.extract(
        "Show top 5 products by revenue"
    )

    assert context.limit == 5
    assert context.sort_direction == "descending"


def test_extract_bottom_limit():

    extractor = create_extractor()

    context = extractor.extract(
        "Show bottom 10 products by revenue"
    )

    assert context.limit == 10
    assert context.sort_direction == "ascending"


# ============================================================
# EXPLICIT YEAR
# ============================================================

def test_extract_year():

    extractor = create_extractor()

    context = extractor.extract(
        "Show revenue in 2025"
    )

    assert context.time_range is not None

    assert context.time_range["type"] == "year"
    assert context.time_range["year"] == 2025
    assert context.time_range["start"] == "2025-01-01"
    assert context.time_range["end"] == "2025-12-31"


# ============================================================
# THIS YEAR
# ============================================================

def test_extract_this_year():

    extractor = create_extractor()

    current_year = date.today().year

    context = extractor.extract(
        "Show revenue this year"
    )

    assert context.time_range is not None
    assert context.time_range["type"] == "year"
    assert context.time_range["year"] == current_year
    assert context.time_range["start"] == (
        f"{current_year}-01-01"
    )
    assert context.time_range["end"] == (
        f"{current_year}-12-31"
    )


# ============================================================
# LAST YEAR
# ============================================================

def test_extract_last_year():

    extractor = create_extractor()

    last_year = date.today().year - 1

    context = extractor.extract(
        "Show revenue last year"
    )

    assert context.time_range is not None
    assert context.time_range["type"] == "year"
    assert context.time_range["year"] == last_year
    assert context.time_range["start"] == (
        f"{last_year}-01-01"
    )
    assert context.time_range["end"] == (
        f"{last_year}-12-31"
    )


# ============================================================
# MONTH + YEAR
# ============================================================

def test_extract_month_and_year():

    extractor = create_extractor()

    context = extractor.extract(
        "Show revenue for January 2025"
    )

    assert context.time_range is not None

    assert context.time_range["type"] == "month"
    assert context.time_range["year"] == 2025
    assert context.time_range["month"] == 1

    assert context.time_range["start"] == (
        "2025-01-01"
    )

    assert context.time_range["end"] == (
        "2025-01-31"
    )


# ============================================================
# FILTER
# ============================================================

def test_extract_customer_location_filter():

    extractor = create_extractor()

    context = extractor.extract(
        "Show products by revenue for customers from Delhi"
    )

    assert context.filters == [
        {
            "field": "customer.city",
            "operator": "=",
            "value": "delhi",
        }
    ]


def test_extract_city_filter():

    extractor = create_extractor()

    context = extractor.extract(
        "Show revenue where city is Delhi"
    )

    assert context.filters == [
        {
            "field": "city",
            "operator": "=",
            "value": "delhi",
        }
    ]


# ============================================================
# CONTEXT PRESERVATION
# ============================================================

def test_followup_preserves_time_range():

    extractor = create_extractor()

    first = extractor.extract(
        "Show top 5 products by revenue in 2025"
    )

    second = extractor.extract(
        "What about quantity?",
        previous_context=first
    )

    assert second.entity == "product"
    assert second.metric == "quantity"
    assert second.aggregation == "sum"
    assert second.limit == 5
    assert second.sort_direction == "descending"

    assert second.time_range == {
        "type": "year",
        "year": 2025,
        "start": "2025-01-01",
        "end": "2025-12-31",
    }


def test_followup_replaces_time_range():

    extractor = create_extractor()

    first = extractor.extract(
        "Show top 5 products by revenue in 2025"
    )

    second = extractor.extract(
        "Show the same for 2024",
        previous_context=first
    )

    assert second.entity == "product"
    assert second.metric == "revenue"
    assert second.limit == 5

    assert second.time_range == {
        "type": "year",
        "year": 2024,
        "start": "2024-01-01",
        "end": "2024-12-31",
    }


def test_followup_preserves_filters():

    extractor = create_extractor()

    first = extractor.extract(
        "Show products by revenue for customers from Delhi"
    )

    second = extractor.extract(
        "What about quantity?",
        previous_context=first
    )

    assert second.metric == "quantity"

    assert second.filters == [
        {
            "field": "customer.city",
            "operator": "=",
            "value": "delhi",
        }
    ]


# ============================================================
# CONTEXT SHOULD NOT MUTATE
# ============================================================

def test_previous_context_is_not_mutated():

    extractor = create_extractor()

    first = extractor.extract(
        "Show top 5 products by revenue in 2025"
    )

    second = extractor.extract(
        "What about quantity?",
        previous_context=first
    )

    assert first.metric == "revenue"
    assert second.metric == "quantity"

    assert first.time_range == second.time_range