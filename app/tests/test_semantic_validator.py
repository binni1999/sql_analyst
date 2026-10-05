from agents.semantic_validator import SemanticValidator
from database.metadata_service import MetadataService


def create_validator():

    metadata_service = MetadataService()

    return SemanticValidator(
        metadata_service=metadata_service
    )


# ---------------------------------------------------------
# Test 1: Correct revenue SQL
# ---------------------------------------------------------

def test_valid_revenue_sql():

    validator = create_validator()

    question = "Show the top 5 products by revenue"

    sql = """
    SELECT
        p.product_id,
        p.product_name,
        SUM(
            oi.quantity
            * oi.unit_price
            * (1 - oi.discount)
        ) AS revenue
    FROM order_items oi
    JOIN products p
        ON oi.product_id = p.product_id
    GROUP BY
        p.product_id,
        p.product_name
    ORDER BY revenue DESC
    LIMIT 5;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is True
    assert result["errors"] == []


# ---------------------------------------------------------
# Test 2: Revenue missing discount
# ---------------------------------------------------------

def test_revenue_missing_discount():

    validator = create_validator()

    question = "Show total revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity * oi.unit_price
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
        "discount" in error.lower()
        for error in result["errors"]
    )


# ---------------------------------------------------------
# Test 3: Revenue missing quantity
# ---------------------------------------------------------

def test_revenue_missing_quantity():

    validator = create_validator()

    question = "Show total revenue"

    sql = """
    SELECT
        SUM(
            oi.unit_price
            * (1 - oi.discount)
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
        "quantity" in error.lower()
        for error in result["errors"]
    )


# ---------------------------------------------------------
# Test 4: Revenue missing unit_price
# ---------------------------------------------------------

def test_revenue_missing_unit_price():

    validator = create_validator()

    question = "Show total revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity
            * (1 - oi.discount)
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
        "unit_price" in error.lower()
        for error in result["errors"]
    )


# ---------------------------------------------------------
# Test 5: Question does not request a metric
# ---------------------------------------------------------

def test_question_without_metric():

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
    assert result["errors"] == []


# ---------------------------------------------------------
# Test 6: Sales should detect revenue metric
# ---------------------------------------------------------

def test_sales_detects_revenue():

    validator = create_validator()

    question = "Show total sales by product"

    sql = """
    SELECT
        p.product_id,
        p.product_name,
        SUM(
            oi.quantity
            * oi.unit_price
            * (1 - oi.discount)
        ) AS revenue
    FROM order_items oi
    JOIN products p
        ON oi.product_id = p.product_id
    GROUP BY
        p.product_id,
        p.product_name;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is True
    assert result["errors"] == []


# ---------------------------------------------------------
# Test 7: Unknown metric reported
# ---------------------------------------------------------

def test_unknown_reported_metric():

    validator = create_validator()

    question = "Show the top products"

    sql = """
    SELECT
        product_id,
        product_name
    FROM products;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["profit"]
    )

    assert result["is_valid"] is False

    assert any(
        "unknown metric" in error.lower()
        for error in result["errors"]
    )


# ---------------------------------------------------------
# Test 8: total_revenue alias
# ---------------------------------------------------------

def test_total_revenue_alias():

    validator = create_validator()

    question = "Show total revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity
            * oi.unit_price
            * (1 - oi.discount)
        ) AS total_revenue
    FROM order_items oi;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is True
    assert result["errors"] == []


# ---------------------------------------------------------
# Test 9: Invalid SQL
# ---------------------------------------------------------

def test_invalid_sql():

    validator = create_validator()

    question = "Show total revenue"

    sql = """
    SELECT
        SUM(
            oi.quantity *
        AS revenue
    FROM order_items oi;
    """

    result = validator.validate(
        question=question,
        sql=sql,
        metrics_used=["revenue"]
    )

    assert result["is_valid"] is False

    assert any(
        "parse" in error.lower()
        for error in result["errors"]
    )