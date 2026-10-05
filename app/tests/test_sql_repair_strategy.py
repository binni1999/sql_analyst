from models.sql_error import SQLError, SQLErrorType
from validation.sql_repair_strategy import SQLRepairStrategy
from models.analytical_context import AnalyticalContext
from models.sql_requirements import SQLRequirements


def test_syntax_repair_instruction():
    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.SYNTAX,
        message="Invalid SQL syntax.",
        source="SQLValidator",
    )

    instruction = strategy.build_instruction(error)

    assert "SQL SYNTAX REPAIR" in instruction
    assert "Invalid SQL syntax." in instruction
    assert "analytical intent" in instruction


def test_database_repair_instruction():
    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.DATABASE,
        message="column does not exist",
        source="DatabaseValidator",
    )

    instruction = strategy.build_instruction(error)

    assert "DATABASE COMPATIBILITY REPAIR" in instruction
    assert "column does not exist" in instruction
    assert "PostgreSQL" in instruction


def test_semantic_repair_instruction():
    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.SEMANTIC,
        message="Revenue formula is incorrect.",
        source="SemanticValidator",
    )

    instruction = strategy.build_instruction(error)

    assert "SEMANTIC REPAIR" in instruction
    assert "Revenue formula is incorrect." in instruction
    assert "business metric" in instruction


def test_context_repair_instruction():
    strategy = SQLRepairStrategy()

    error = SQLError(
        error_type=SQLErrorType.CONTEXT,
        message="Expected DESC ordering but found ASC.",
        source="ContextValidator",
    )

    instruction = strategy.build_instruction(error)

    assert "ANALYTICAL CONTEXT REPAIR" in instruction
    assert "Expected DESC ordering but found ASC." in instruction
    assert "sort direction" in instruction


def test_build_instructions_for_multiple_errors():
    strategy = SQLRepairStrategy()

    errors = [
        SQLError(
            error_type=SQLErrorType.SYNTAX,
            message="Invalid syntax.",
            source="SQLValidator",
        ),
        SQLError(
            error_type=SQLErrorType.SEMANTIC,
            message="Invalid revenue formula.",
            source="SemanticValidator",
        ),
        SQLError(
            error_type=SQLErrorType.CONTEXT,
            message="Expected LIMIT 5.",
            source="ContextValidator",
        ),
    ]

    instructions = strategy.build_instructions(errors)

    assert len(instructions) == 3

    assert "SQL SYNTAX REPAIR" in instructions[0]
    assert "SEMANTIC REPAIR" in instructions[1]
    assert "ANALYTICAL CONTEXT REPAIR" in instructions[2]


def test_empty_error_list():
    strategy = SQLRepairStrategy()

    instructions = strategy.build_instructions([])

    assert instructions == []

def test_context_repair_includes_analytical_context():

    strategy = SQLRepairStrategy()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    error = SQLError(
        error_type=SQLErrorType.CONTEXT,
        message="Expected DESC ordering but found ASC.",
        source="ContextValidator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
    )

    assert "ANALYTICAL CONTEXT REPAIR" in instruction
    assert "Expected DESC ordering but found ASC." in instruction

    assert '"entity": "product"' in instruction
    assert '"metric": "revenue"' in instruction
    assert '"limit": 5' in instruction
    assert '"sort_direction": "desc"' in instruction

def test_context_repair_includes_sql_requirements():

    strategy = SQLRepairStrategy()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    requirements = SQLRequirements(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    error = SQLError(
        error_type=SQLErrorType.CONTEXT,
        message="Expected LIMIT 5.",
        source="ContextValidator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
        requirements=requirements,
    )

    assert "SQL REQUIREMENTS" in instruction
    assert '"limit": 5' in instruction
    assert '"sort_direction": "desc"' in instruction

def test_semantic_repair_includes_analytical_context():

    strategy = SQLRepairStrategy()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
    )

    error = SQLError(
        error_type=SQLErrorType.SEMANTIC,
        message="Revenue formula is incorrect.",
        source="SemanticValidator",
    )

    instruction = strategy.build_instruction(
        error,
        analytical_context=context,
    )

    assert "SEMANTIC REPAIR" in instruction
    assert "Revenue formula is incorrect." in instruction
    assert '"metric": "revenue"' in instruction





