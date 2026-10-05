from models.analytical_context import AnalyticalContext
from models.sql_error import SQLError, SQLErrorType
from models.sql_requirements import SQLRequirements

from validation.sql_repair_strategy import SQLRepairStrategy


def create_context():
    return AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
        filters=[
            {
                "field": "category",
                "operator": "=",
                "value": "Electronics",
            }
        ],
        time_range={
            "type": "year",
            "year": 2025,
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
    )


def create_requirements():
    return SQLRequirements(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
        filters=[
            {
                "field": "category",
                "operator": "=",
                "value": "Electronics",
            }
        ],
        time_range={
            "type": "year",
            "year": 2025,
            "start": "2025-01-01",
            "end": "2025-12-31",
        },
    )


def test_context_repair_preserves_analytical_context():

    strategy = SQLRepairStrategy()

    context = create_context()

    error = SQLError(
        error_type=SQLErrorType.CONTEXT,
        message="Expected DESC ordering but found ASC.",
        source="context_validator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
    )

    assert "ANALYTICAL CONTEXT REPAIR" in instruction

    assert "product" in instruction
    assert "revenue" in instruction
    assert "sum" in instruction
    assert "5" in instruction
    assert "desc" in instruction

    assert "category" in instruction
    assert "Electronics" in instruction

    assert "2025-01-01" in instruction
    assert "2025-12-31" in instruction

    assert "Expected DESC ordering but found ASC." in instruction


def test_context_repair_includes_sql_requirements():

    strategy = SQLRepairStrategy()

    context = create_context()
    requirements = create_requirements()

    error = SQLError(
        error_type=SQLErrorType.CONTEXT,
        message="Expected LIMIT 5 but found LIMIT 10.",
        source="context_validator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
        requirements=requirements,
    )

    assert "ANALYTICAL CONTEXT:" in instruction
    assert "SQL REQUIREMENTS:" in instruction

    assert '"entity": "product"' in instruction
    assert '"metric": "revenue"' in instruction
    assert '"aggregation": "sum"' in instruction
    assert '"limit": 5' in instruction
    assert '"sort_direction": "desc"' in instruction

    assert "Expected LIMIT 5 but found LIMIT 10." in instruction


def test_semantic_repair_preserves_metric_intent():

    strategy = SQLRepairStrategy()

    context = create_context()
    requirements = create_requirements()

    error = SQLError(
        error_type=SQLErrorType.SEMANTIC,
        message="Revenue formula is incorrect.",
        source="semantic_validator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
        requirements=requirements,
    )

    assert "SEMANTIC REPAIR" in instruction

    assert "business metric" in instruction
    assert "defined formula" in instruction
    assert "preserved exactly" in instruction

    assert "revenue" in instruction
    assert "sum" in instruction

    assert "ANALYTICAL CONTEXT:" in instruction
    assert "SQL REQUIREMENTS:" in instruction

    assert "Revenue formula is incorrect." in instruction


def test_syntax_repair_does_not_require_context():

    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.SYNTAX,
        message="Unexpected token near SELECT.",
        source="sqlglot",
    )

    instruction = strategy.build_instruction(error)

    assert "SQL SYNTAX REPAIR" in instruction
    assert "Unexpected token near SELECT." in instruction

    assert "ANALYTICAL CONTEXT:" not in instruction
    assert "SQL REQUIREMENTS:" not in instruction


def test_database_repair_targets_postgresql_compatibility():

    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.DATABASE,
        message='column "foo" does not exist',
        source="postgresql",
    )

    instruction = strategy.build_instruction(error)

    assert "DATABASE COMPATIBILITY REPAIR" in instruction
    assert "PostgreSQL dialect" in instruction
    assert "table names" in instruction
    assert "column names" in instruction
    assert "joins" in instruction

    assert 'column "foo" does not exist' in instruction