from agents.sql_agent import SQLAgent


SCHEMAS = [
    {
        "table": "order_items",
        "columns": [
            {"name": "quantity"},
            {"name": "unit_price"},
            {"name": "discount"},
        ],
    },
    {
        "table": "orders",
        "columns": [{"name": "order_id"}, {"name": "customer_id"}],
    },
]


def test_rejects_explicit_nonexistent_table_request():
    errors = SQLAgent._validate_explicit_schema_intent(
        "Show total revenue from the imaginary_sales table.", SCHEMAS
    )
    assert errors
    assert "Unknown table requested: 'imaginary_sales'" in errors[0]


def test_rejects_explicit_nonexistent_grouping_column():
    errors = SQLAgent._validate_explicit_schema_intent(
        "Show the total revenue grouped by customer_favorite_color.", SCHEMAS
    )
    assert errors
    assert "Unknown column requested: 'customer_favorite_color'" in errors[0]


def test_does_not_reject_valid_natural_language_grouping():
    errors = SQLAgent._validate_explicit_schema_intent(
        "Show total revenue grouped by product.", SCHEMAS
    )
    assert errors == []


def test_does_not_reject_question_without_explicit_invalid_identifier():
    errors = SQLAgent._validate_explicit_schema_intent(
        "Show the top 5 products by revenue.", SCHEMAS
    )
    assert errors == []
