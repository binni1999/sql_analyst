# pyrefly: ignore [missing-import]
from test_semantic_validator import create_validator
def test_correct_revenue_formula():

    validator = create_validator()

    question = "Show revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity
            * oi.unit_price
            * (1 - oi.discount)
        ) AS revenue
    FROM order_items oi;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is True

def test_incorrect_revenue_formula():

    validator = create_validator()

    question = "Show revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity
            * oi.unit_price
            + oi.discount
        ) AS revenue
    FROM order_items oi;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is False

    assert any(
        "expected formula" in error.lower()
        for error in result["errors"]
    )

def test_formula_missing_discount():

    validator = create_validator()

    question = "Show revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity
            * oi.unit_price
        ) AS revenue
    FROM order_items oi;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is False


def test_no_metric_question():

    validator = create_validator()

    question = "Show all customers"

    sql = """
    SELECT
        customer_id,
        first_name,
        last_name
    FROM customers;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=[]
    )

    assert result["is_valid"] is True

