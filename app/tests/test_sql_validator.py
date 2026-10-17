
import pytest

# pyrefly: ignore [missing-import]
from agents.sql_validator import SQLValidator


@pytest.fixture
def validator():
    return SQLValidator()


@pytest.fixture
def schemas():
    return [
        {
            "table": "products",
            "columns": [
                {"name": "product_id", "type": "integer"},
                {"name": "product_name", "type": "varchar"},
                {"name": "price", "type": "numeric"},
            ],
        },
        {
            "table": "customers",
            "columns": [
                {"name": "customer_id", "type": "integer"},
                {"name": "first_name", "type": "varchar"},
            ],
        },
    ]


def test_valid_select_passes(validator, schemas):
    result = validator.validate(
        "SELECT product_id, product_name FROM products",
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []



def test_invalid_sql_returns_syntax_error(validator, schemas):
    result = validator.validate(
        "SELECT * FROM",
        schemas,
    )

    assert result.is_valid is False
    assert len(result.errors) > 0



def test_unknown_table_is_rejected(validator, schemas):
    result = validator.validate(
        "SELECT product_id FROM missing_products",
        schemas,
    )

    assert result.is_valid is False
    assert any("unknown table" in error.lower() for error in result.errors)


def test_unknown_qualified_column_is_rejected(validator, schemas):
    result = validator.validate(
        "SELECT p.unknown_column FROM products p",
        schemas,
    )

    assert result.is_valid is False
    assert any("unknown column" in error.lower() for error in result.errors)


@pytest.mark.parametrize(
    ("sql", "operation"),
    [
        ("DELETE FROM products", "Delete"),
        ("UPDATE products SET price = 10", "Update"),
        ("INSERT INTO products (product_id) VALUES (1)", "Insert"),
        ("DROP TABLE products", "Drop"),
        ("TRUNCATE TABLE products", "TruncateTable"),
    ],
)
def test_write_operations_are_rejected(validator, schemas, sql, operation):
    result = validator.validate(sql, schemas)

    assert result.is_valid is False
    assert any(operation in error for error in result.errors)


def test_table_alias_is_supported(validator, schemas):
    result = validator.validate(
        "SELECT p.product_name FROM products AS p",
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_cte_is_supported(validator, schemas):
    result = validator.validate(
        """
        WITH product_list AS (
            SELECT product_id, product_name
            FROM products
        )
        SELECT product_list.product_name
        FROM product_list
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_duplicate_validation_errors_are_removed(validator, schemas):
    result = validator.validate(
        "SELECT p.missing_column FROM products p",
        schemas,
    )

    assert len(result.errors) == len(set(result.errors))



def test_ambiguous_unqualified_column_is_rejected(validator):
    schemas = [
        {"table": "products", "columns": [
            {"name": "product_id", "type": "integer"},
            {"name": "name", "type": "varchar"},
        ]},
        {"table": "customers", "columns": [
            {"name": "customer_id", "type": "integer"},
            {"name": "name", "type": "varchar"},
        ]},
    ]

    result = validator.validate(
        "SELECT name FROM products p JOIN customers c "
        "ON p.product_id = c.customer_id",
        schemas,
    )

    assert result.is_valid is False
    assert any("ambiguous column" in error.lower() for error in result.errors)



def test_unknown_unqualified_column_preserves_current_behavior(
    validator, schemas
):
    result = validator.validate(
        "SELECT nonexistent_column FROM products",
        schemas,
    )

    # The current validator deliberately permits unresolved
    # unqualified columns when ownership cannot be determined.
    assert result.is_valid is True



def test_derived_table_alias_is_supported(validator, schemas):
    result = validator.validate(
        """
        SELECT p.product_name
        FROM (
            SELECT product_id, product_name
            FROM products
        ) AS p
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_unknown_column_in_derived_table_is_rejected(validator, schemas):
    result = validator.validate(
        """
        SELECT p.missing_column
        FROM (
            SELECT product_id, product_name
            FROM products
        ) AS p
        """,
        schemas,
    )

    assert result.is_valid is False
    assert any("unknown column" in error.lower() for error in result.errors)


def test_cte_explicit_column_list_is_supported(validator, schemas):
    result = validator.validate(
        """
        WITH product_list (id, label) AS (
            SELECT product_id, product_name
            FROM products
        )
        SELECT product_list.label
        FROM product_list
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_order_by_select_alias_is_supported(validator, schemas):
    result = validator.validate(
        """
        SELECT product_name AS label
        FROM products
        ORDER BY label
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_unknown_table_alias_is_rejected(validator, schemas):
    result = validator.validate(
        "SELECT x.product_name FROM products p",
        schemas,
    )

    assert result.is_valid is False
    assert any(
        "unknown table or alias" in error.lower()
        for error in result.errors
    )



def test_unqualified_column_from_derived_table_is_supported(
    validator, schemas
):
    result = validator.validate(
        """
        SELECT product_name
        FROM (
            SELECT product_id, product_name
            FROM products
        ) AS p
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_derived_table_aggregate_alias_is_supported(
    validator, schemas
):
    result = validator.validate(
        """
        SELECT p.total_price
        FROM (
            SELECT SUM(price) AS total_price
            FROM products
        ) AS p
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_cte_aggregate_alias_is_supported(validator, schemas):
    result = validator.validate(
        """
        WITH product_summary AS (
            SELECT SUM(price) AS total_price
            FROM products
        )
        SELECT product_summary.total_price
        FROM product_summary
        """,
        schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_cte_unknown_output_column_is_rejected(validator, schemas):
    result = validator.validate(
        """
        WITH product_list AS (
            SELECT product_id, product_name
            FROM products
        )
        SELECT product_list.missing_column
        FROM product_list
        """,
        schemas,
    )

    assert result.is_valid is False
    assert any(
        "unknown column" in error.lower()
        for error in result.errors
    )
