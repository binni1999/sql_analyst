from models.sql_requirements import SQLRequirements
from validation.context_validator import ContextValidator


def test_valid_limit():

    validator = ContextValidator()

    requirements = SQLRequirements(
        limit=5
    )

    result = validator.validate(
        """
        SELECT product_id
        FROM products
        LIMIT 5
        """,
        requirements
    )

    assert result.is_valid is True
    assert result.errors == []


def test_invalid_limit():

    validator = ContextValidator()

    requirements = SQLRequirements(
        limit=5
    )

    result = validator.validate(
        """
        SELECT product_id
        FROM products
        LIMIT 10
        """,
        requirements
    )

    assert result.is_valid is False
    assert any(
        "Expected LIMIT 5" in error
        for error in result.errors
    )


def test_missing_limit():

    validator = ContextValidator()

    requirements = SQLRequirements(
        limit=5
    )

    result = validator.validate(
        """
        SELECT product_id
        FROM products
        """,
        requirements
    )

    assert result.is_valid is False


def test_valid_descending_order():

    validator = ContextValidator()

    requirements = SQLRequirements(
        sort_direction="desc"
    )

    result = validator.validate(
        """
        SELECT
            product_id,
            SUM(quantity) AS revenue
        FROM order_items
        GROUP BY product_id
        ORDER BY revenue DESC
        """,
        requirements
    )

    assert result.is_valid is True


def test_invalid_order_direction():

    validator = ContextValidator()

    requirements = SQLRequirements(
        sort_direction="desc"
    )

    result = validator.validate(
        """
        SELECT
            product_id,
            SUM(quantity) AS revenue
        FROM order_items
        GROUP BY product_id
        ORDER BY revenue ASC
        """,
        requirements
    )

    assert result.is_valid is False

    assert any(
        "DESC" in error
        for error in result.errors
    )


def test_grouping_required():

    validator = ContextValidator()

    requirements = SQLRequirements(
        entity="product",
        group_by_required=True
    )

    result = validator.validate(
        """
        SELECT
            product_id,
            SUM(quantity)
        FROM order_items
        """,
        requirements
    )

    assert result.is_valid is False

    assert any(
        "GROUP BY" in error
        for error in result.errors
    )


def test_grouping_present():

    validator = ContextValidator()

    requirements = SQLRequirements(
        entity="product",
        group_by_required=True
    )

    result = validator.validate(
        """
        SELECT
            product_id,
            SUM(quantity)
        FROM order_items
        GROUP BY product_id
        """,
        requirements
    )

    assert result.is_valid is True


def test_time_range_with_date_literals():

    validator = ContextValidator()

    requirements = SQLRequirements(
        time_range={
            "type": "year",
            "year": 2025,
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
        time_range_required=True,
    )

    result = validator.validate(
        """
        SELECT
            SUM(quantity)
        FROM order_items
        WHERE order_date >= '2025-01-01'
          AND order_date <= '2025-12-31'
        """,
        requirements
    )

    assert result.is_valid is True


def test_missing_time_range():

    validator = ContextValidator()

    requirements = SQLRequirements(
        time_range={
            "type": "year",
            "year": 2025,
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
        time_range_required=True,
    )

    result = validator.validate(
        """
        SELECT
            SUM(quantity)
        FROM order_items
        """,
        requirements
    )

    assert result.is_valid is False


def test_required_filter_field():

    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    result = validator.validate(
        """
        SELECT *
        FROM customers
        WHERE city = 'Delhi'
        """,
        requirements
    )

    assert result.is_valid is True


def test_missing_required_filter_field():

    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    result = validator.validate(
        """
        SELECT *
        FROM customers
        """,
        requirements
    )

    assert result.is_valid is False


def test_empty_sql_is_invalid():

    validator = ContextValidator()

    requirements = SQLRequirements()

    result = validator.validate(
        "",
        requirements
    )

    assert result.is_valid is False
    assert "empty" in result.errors[0].lower()


def test_invalid_sql_is_invalid():

    validator = ContextValidator()

    requirements = SQLRequirements()

    result = validator.validate(
        "SELECT FROM",
        requirements
    )

    assert result.is_valid is False


def test_valid_filter_with_schema():
    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    schemas = [
        {
            "table": "customers",
            "columns": [
                {"name": "id"},
                {"name": "name"},
                {"name": "city"},
            ],
        }
    ]

    sql = """
        SELECT *
        FROM customers
        WHERE city = 'Delhi'
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_filter_field_does_not_exist_in_schema():
    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    schemas = [
        {
            "table": "customers",
            "columns": [
                {"name": "id"},
                {"name": "name"},
            ],
        }
    ]

    sql = """
        SELECT *
        FROM customers
        WHERE city = 'Delhi'
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is False
    assert any(
        "does not exist in the database schema" in error
        for error in result.errors
    )


def test_filter_field_referenced_but_not_used_as_predicate():
    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    schemas = [
        {
            "table": "customers",
            "columns": [
                {"name": "id"},
                {"name": "name"},
                {"name": "city"},
            ],
        }
    ]

    sql = """
        SELECT city
        FROM customers
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is False
    assert any(
        "not used in a filter predicate" in error
        for error in result.errors
    )


def test_qualified_filter_column_is_valid():
    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    schemas = [
        {
            "table": "customers",
            "columns": [
                {"name": "id"},
                {"name": "name"},
                {"name": "city"},
            ],
        }
    ]

    sql = """
        SELECT *
        FROM customers
        WHERE customers.city = 'Delhi'
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is True


def test_valid_group_by_column_with_schema():
    validator = ContextValidator()

    requirements = SQLRequirements(
        entity="product",
        group_by_required=True,
    )

    schemas = [
        {
            "table": "products",
            "columns": [
                {"name": "id"},
                {"name": "name"},
            ],
        }
    ]

    sql = """
        SELECT products.name, COUNT(*)
        FROM products
        GROUP BY products.name
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is True
    assert result.errors == []


def test_group_by_column_does_not_exist_in_schema():
    validator = ContextValidator()

    requirements = SQLRequirements(
        entity="product",
        group_by_required=True,
    )

    schemas = [
        {
            "table": "products",
            "columns": [
                {"name": "id"},
                {"name": "name"},
            ],
        }
    ]

    sql = """
        SELECT products.category, COUNT(*)
        FROM products
        GROUP BY products.category
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
        schemas=schemas,
    )

    assert result.is_valid is False
    assert any(
        "GROUP BY column 'category'" in error
        for error in result.errors
    )


def test_schema_is_optional_and_existing_behavior_is_preserved():
    validator = ContextValidator()

    requirements = SQLRequirements(
        filters=[
            {
                "field": "city",
                "operator": "=",
                "value": "Delhi",
            }
        ]
    )

    sql = """
        SELECT *
        FROM customers
        WHERE city = 'Delhi'
    """

    result = validator.validate(
        sql=sql,
        requirements=requirements,
    )

    assert result.is_valid is True
    assert result.errors == []