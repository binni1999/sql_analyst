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



def test_count_star_does_not_trigger_wildcard_projection_warning():
    result = SQLRiskChecker().assess(
        "SELECT COUNT(*) FROM customers"
    )

    assert not any(
        "Wildcard projection" in reason
        for reason in result.reasons
    )


def test_select_star_without_limit_triggers_wildcard_projection_warning():
    result = SQLRiskChecker().assess(
        "SELECT * FROM customers"
    )

    assert result.is_risky is True
    assert any(
        "Wildcard projection" in reason
        for reason in result.reasons
    )

def test_count_star_warning_does_not_claim_wildcard_projection():
    result = SQLRiskChecker().assess(
        "SELECT COUNT(*) FROM customers"
    )

    assert result.is_risky is True
    assert any(
        "aggregation" in reason.lower()
        for reason in result.reasons
    )
    assert not any(
        "wildcard projection" in reason.lower()
        for reason in result.reasons
    )

def test_grouped_aggregation_without_limit_requires_review():
    result = SQLRiskChecker().assess(
        "SELECT city, COUNT(*) AS customer_count "
        "FROM customers GROUP BY city"
    )

    assert result.is_risky is True
    assert any(
        "aggregation" in reason.lower()
        for reason in result.reasons
    )


def test_aggregation_with_where_and_without_other_risks_is_safe():
    result = SQLRiskChecker().assess(
        "SELECT COUNT(*) FROM customers WHERE city = 'Delhi'"
    )

    assert result.is_risky is False
    assert result.risk_level == "low"

    