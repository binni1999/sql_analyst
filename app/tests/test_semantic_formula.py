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



def test_revenue_formula_in_derived_table():
    validator = create_validator()

    sql = """
    SELECT p.product_name, ROUND(pr.revenue, 2) AS revenue
    FROM (
        SELECT product_id,
               SUM(quantity * unit_price * (1 - discount)) AS revenue
        FROM order_items
        GROUP BY product_id
    ) pr
    JOIN products p ON p.product_id = pr.product_id
    ORDER BY pr.revenue DESC
    LIMIT 5
    """

    result = validator.validate(
        question="Show the top 5 products by revenue",
        sql=sql,
        metrics_used=["revenue"],
    )

    assert result["is_valid"] is True
    assert result["errors"] == []


def test_revenue_formula_in_cte():
    validator = create_validator()

    sql = """
    WITH rev AS (
        SELECT p.product_id, p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        GROUP BY p.product_id, p.product_name
    )
    SELECT product_name, ROUND(revenue, 2) AS revenue
    FROM rev
    ORDER BY revenue DESC
    LIMIT 5
    """

    result = validator.validate(
        question="Show the top 5 products by revenue",
        sql=sql,
        metrics_used=["revenue"],
    )

    assert result["is_valid"] is True
    assert result["errors"] == []




def test_rounded_revenue_formula_is_valid():
    validator = create_validator()

    sql = """
    SELECT
        ROUND(
            SUM(oi.quantity * oi.unit_price * (1 - oi.discount)),
            2
        ) AS revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.product_id, p.product_name
    """

    result = validator.validate(
        question="Show revenue rounded to 2 decimal places",
        sql=sql,
        metrics_used=["revenue"],
    )

    assert result["is_valid"] is True
    assert result["errors"] == []


def test_rounded_incorrect_revenue_formula_is_invalid():
    validator = create_validator()

    sql = """
    SELECT
        ROUND(
            SUM(oi.quantity * oi.unit_price + oi.discount),
            2
        ) AS revenue
    FROM order_items oi
    GROUP BY oi.product_id
    """

    result = validator.validate(
        question="Show revenue rounded to 2 decimal places",
        sql=sql,
        metrics_used=["revenue"],
    )

    assert result["is_valid"] is False
    assert any(
        "expected formula" in error.lower()
        for error in result["errors"]
    )
