import pytest

from security.policies import SQLSecurityPolicy


def test_policy_normalizes_allowed_table_names():
    policy = SQLSecurityPolicy(
        allowed_tables=frozenset({"Products", "ORDERS"})
    )

    assert policy.normalized_allowed_tables() == frozenset({"products", "orders"})


def test_policy_normalizes_allowed_column_names():
    policy = SQLSecurityPolicy(
        allowed_columns={
            "Products": frozenset({"Product_ID", "NAME"})
        }
    )

    assert policy.normalized_allowed_columns() == {
        "products": frozenset({"product_id", "name"})
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_query_length", 0),
        ("max_joins", -1),
        ("max_subqueries", -1),
        ("max_result_rows", 0),
    ],
)
def test_invalid_policy_limits_are_rejected(field, value):
    with pytest.raises(ValueError):
        SQLSecurityPolicy(**{field: value})


def test_policy_normalizes_sensitive_column_names():
    policy = SQLSecurityPolicy(
        sensitive_columns={"Customers": frozenset({"Email", "PHONE"})}
    )

    assert policy.normalized_sensitive_columns() == {
        "customers": frozenset({"email", "phone"})
    }
