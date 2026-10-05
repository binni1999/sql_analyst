from services.sql_risk_checker import SQLRiskChecker


def test_simple_select_is_safe():
    result = SQLRiskChecker().assess("SELECT 1")
    assert result.is_risky is False
    assert result.risk_level == "low"


def test_top_n_joined_query_with_limit_is_safe():
    result = SQLRiskChecker().assess(
        "SELECT p.name, SUM(oi.quantity) AS total "
        "FROM products p JOIN order_items oi ON oi.product_id = p.id "
        "GROUP BY p.name ORDER BY total DESC LIMIT 5"
    )
    assert result.is_risky is False


def test_join_without_limit_requires_approval():
    result = SQLRiskChecker().assess(
        "SELECT p.name, SUM(oi.quantity) AS total "
        "FROM products p JOIN order_items oi ON oi.product_id = p.id "
        "GROUP BY p.name ORDER BY total DESC"
    )
    assert result.is_risky is True
    assert result.risk_level == "medium"
    assert result.reasons


def test_cross_join_is_high_risk():
    result = SQLRiskChecker().assess(
        "SELECT * FROM customers CROSS JOIN orders"
    )
    assert result.is_risky is True
    assert result.risk_level == "high"


def test_unfiltered_aggregation_requires_approval():
    result = SQLRiskChecker().assess(
        "SELECT COUNT(*) FROM orders"
    )
    assert result.is_risky is True


def test_invalid_sql_is_flagged_for_review():
    result = SQLRiskChecker().assess("SELECT FROM")
    assert result.is_risky is True
    assert result.risk_level == "high"
