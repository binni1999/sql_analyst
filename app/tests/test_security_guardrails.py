from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy


def test_select_query_is_allowed():
    result = SQLSecurityGuardrail().validate(
        "SELECT product_id FROM products"
    )

    assert result.allowed is True
    assert result.violations == []
    assert result.normalized_sql


def test_empty_sql_is_blocked():
    result = SQLSecurityGuardrail().validate("   ")

    assert result.allowed is False
    assert result.violations[0].rule == "empty_sql"


def test_insert_is_blocked():
    result = SQLSecurityGuardrail().validate(
        "INSERT INTO products(product_name) VALUES ('x')"
    )

    assert result.allowed is False
    assert any(v.rule == "select_only" for v in result.violations)


def test_update_is_blocked():
    result = SQLSecurityGuardrail().validate(
        "UPDATE products SET product_name = 'x'"
    )

    assert result.allowed is False
    assert any(v.rule == "select_only" for v in result.violations)


def test_delete_is_blocked():
    result = SQLSecurityGuardrail().validate(
        "DELETE FROM products"
    )

    assert result.allowed is False
    assert any(v.rule == "select_only" for v in result.violations)


def test_drop_is_blocked():
    result = SQLSecurityGuardrail().validate(
        "DROP TABLE products"
    )

    assert result.allowed is False
    assert any(v.rule == "select_only" for v in result.violations)


def test_multiple_statements_are_blocked():
    result = SQLSecurityGuardrail().validate(
        "SELECT * FROM products; DROP TABLE products;"
    )

    assert result.allowed is False
    assert any(v.rule == "single_statement" for v in result.violations)


def test_unauthorized_table_is_blocked():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products", "orders"})
        )
    )

    result = guardrail.validate(
        "SELECT * FROM customers"
    )

    assert result.allowed is False
    assert any(v.rule == "table_authorization" for v in result.violations)


def test_authorized_table_is_allowed():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products", "orders"})
        )
    )

    result = guardrail.validate(
        "SELECT product_id FROM PRODUCTS"
    )

    assert result.allowed is True


def test_cte_reference_is_not_treated_as_physical_table():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"order_items"})
        )
    )

    result = guardrail.validate(
        """
        WITH totals AS (
            SELECT product_id, SUM(quantity) AS quantity
            FROM order_items
            GROUP BY product_id
        )
        SELECT product_id, quantity
        FROM totals
        LIMIT 100
        """
    )

    assert result.allowed is True


def test_query_length_is_enforced():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(max_query_length=20)
    )

    result = guardrail.validate("SELECT * FROM products")

    assert result.allowed is False
    assert any(v.rule == "query_length" for v in result.violations)


def test_subqueries_can_be_disabled_by_policy():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(allow_subqueries=False)
    )

    result = guardrail.validate(
        "SELECT * FROM products WHERE product_id IN "
        "(SELECT product_id FROM order_items)"
    )

    assert result.allowed is False
    assert any(v.rule == "subquery_policy" for v in result.violations)


def test_authorized_columns_are_allowed():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={
                "products": frozenset({"product_id", "product_name"})
            },
        )
    )

    result = guardrail.validate(
        "SELECT product_id, product_name FROM products"
    )

    assert result.allowed is True


def test_unauthorized_column_is_blocked():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={
                "products": frozenset({"product_id", "product_name"})
            },
        )
    )

    result = guardrail.validate(
        "SELECT product_id, cost FROM products"
    )

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_qualified_column_is_authorized_case_insensitively():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={
                "products": frozenset({"product_id"})
            },
        )
    )

    result = guardrail.validate(
        "SELECT P.PRODUCT_ID FROM PRODUCTS AS P"
    )

    assert result.allowed is True


def test_table_alias_is_resolved_for_column_authorization():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={
                "products": frozenset({"product_id"})
            },
        )
    )

    result = guardrail.validate(
        "SELECT p.product_name FROM products p"
    )

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_join_columns_are_checked_against_each_authorized_table():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products", "orders"}),
            allowed_columns={
                "products": frozenset({"product_id", "product_name"}),
                "orders": frozenset({"order_id", "product_id"}),
            },
        )
    )

    result = guardrail.validate(
        """
        SELECT p.product_name, o.order_id
        FROM products p
        JOIN orders o ON p.product_id = o.product_id
        """
    )

    assert result.allowed is True


def test_unauthorized_join_column_is_blocked():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products", "orders"}),
            allowed_columns={
                "products": frozenset({"product_id", "product_name"}),
                "orders": frozenset({"order_id"}),
            },
        )
    )

    result = guardrail.validate(
        """
        SELECT p.product_name, o.product_id
        FROM products p
        JOIN orders o ON p.product_id = o.product_id
        """
    )

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_wildcard_is_blocked_when_column_policy_applies():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={"products": frozenset({"product_id"})},
        )
    )

    result = guardrail.validate("SELECT * FROM products")

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_qualified_wildcard_is_blocked_when_column_policy_applies():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"products"}),
            allowed_columns={"products": frozenset({"product_id"})},
        )
    )

    result = guardrail.validate("SELECT p.* FROM products p")

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_sensitive_column_is_blocked():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"customers"}),
            sensitive_columns={"customers": frozenset({"email"})},
        )
    )

    result = guardrail.validate("SELECT email FROM customers")

    assert result.allowed is False
    assert any(v.rule == "sensitive_column" for v in result.violations)


def test_sensitive_column_is_blocked_even_if_allowlisted():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"customers"}),
            allowed_columns={"customers": frozenset({"customer_id", "email"})},
            sensitive_columns={"customers": frozenset({"email"})},
        )
    )

    result = guardrail.validate("SELECT email FROM customers")

    assert result.allowed is False
    assert any(v.rule == "sensitive_column" for v in result.violations)


def test_cte_body_columns_are_still_authorized():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"customers"}),
            allowed_columns={"customers": frozenset({"customer_id"})},
        )
    )

    result = guardrail.validate(
        """
        WITH safe_customers AS (
            SELECT customer_id, email
            FROM customers
        )
        SELECT customer_id FROM safe_customers
        """
    )

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_cte_wildcard_does_not_bypass_sensitive_column_protection():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset({"customers"}),
            sensitive_columns={"customers": frozenset({"email"})},
        )
    )

    result = guardrail.validate(
        """
        WITH customer_data AS (
            SELECT * FROM customers
        )
        SELECT * FROM customer_data
        """
    )

    assert result.allowed is False
    assert any(v.rule == "column_authorization" for v in result.violations)


def test_query_within_join_limit_is_allowed():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_joins=2))

    result = guardrail.validate(
        "SELECT p.product_id FROM products p "
        "JOIN order_items oi ON oi.product_id = p.product_id "
        "JOIN orders o ON o.order_id = oi.order_id"
    )

    assert result.allowed is True


def test_query_exceeding_join_limit_is_blocked():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_joins=1))

    result = guardrail.validate(
        "SELECT p.product_id FROM products p "
        "JOIN order_items oi ON oi.product_id = p.product_id "
        "JOIN orders o ON o.order_id = oi.order_id"
    )

    assert result.allowed is False
    assert any(v.rule == "max_joins" for v in result.violations)


def test_nested_joins_are_counted_toward_join_limit():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_joins=1))

    result = guardrail.validate(
        "SELECT p.product_id FROM products p "
        "JOIN order_items oi ON oi.product_id = p.product_id "
        "JOIN orders o ON o.order_id = oi.order_id"
    )

    assert result.allowed is False
    assert [v.rule for v in result.violations].count("max_joins") == 1


def test_query_within_subquery_limit_is_allowed():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_subqueries=1))

    result = guardrail.validate(
        "SELECT product_id FROM products "
        "WHERE product_id IN (SELECT product_id FROM order_items)"
    )

    assert result.allowed is True


def test_query_exceeding_subquery_limit_is_blocked():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_subqueries=1))

    result = guardrail.validate(
        "SELECT product_id FROM products "
        "WHERE product_id IN (SELECT product_id FROM order_items "
        "WHERE order_id IN (SELECT order_id FROM orders))"
    )

    assert result.allowed is False
    assert any(v.rule == "max_subqueries" for v in result.violations)


def test_cte_does_not_count_as_subquery_by_itself():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy(max_subqueries=0))

    result = guardrail.validate(
        "WITH recent_orders AS (SELECT order_id FROM orders) "
        "SELECT order_id FROM recent_orders LIMIT 10"
    )

    assert result.allowed is True


def test_wildcard_without_limit_is_blocked():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy())

    result = guardrail.validate("SELECT * FROM products")

    assert result.allowed is False
    assert any(v.rule == "wildcard_requires_limit" for v in result.violations)


def test_qualified_wildcard_without_limit_is_blocked():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy())

    result = guardrail.validate("SELECT p.* FROM products p")

    assert result.allowed is False
    assert any(v.rule == "wildcard_requires_limit" for v in result.violations)


def test_wildcard_with_limit_is_allowed():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy())

    result = guardrail.validate("SELECT * FROM products LIMIT 100")

    assert result.allowed is True


def test_count_star_is_not_treated_as_wildcard_result():
    guardrail = SQLSecurityGuardrail(SQLSecurityPolicy())

    result = guardrail.validate("SELECT COUNT(*) FROM orders")

    assert result.allowed is True


def test_complexity_policy_can_disable_wildcard_limit_requirement():
    guardrail = SQLSecurityGuardrail(
        SQLSecurityPolicy(require_limit_for_wildcard=False)
    )

    result = guardrail.validate("SELECT * FROM products")

    assert result.allowed is True
