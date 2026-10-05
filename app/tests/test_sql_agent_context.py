from models.analytical_context import AnalyticalContext
from models.execution_trace import ExecutionTraceEvent
from models.agent import MetadataResult
from models.state import AgentState

from models.context_validation import ContextValidationResult

from agents.sql_agent import SQLAgent
from models.sql_error import SQLErrorType


class FakeSQLGenerator:

    def __init__(self):
        self.generate_context = None
        self.fix_context = None

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.generate_context = analytical_context

        class Result:
            sql = "SELECT 1"
            metrics_used = []
            tables_used = []
            explanation = "Test query"

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_context = analytical_context

        return "SELECT 1"


class RepairTrackingSQLGenerator:

    def __init__(self):
        self.fix_errors = None

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        class Result:
            sql = "SELECT 1"
            metrics_used = []
            tables_used = []
            explanation = "Test query"

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_errors = errors

        return "SELECT 1"


class FakeRepairStrategy:

    def __init__(self):
        self.received_errors = None
        self.received_context = None
        self.received_requirements = None

    def build_instructions(
        self,
        errors,
        analytical_context=None,
        requirements=None,
    ):

        self.received_errors = errors
        self.received_context = analytical_context
        self.received_requirements = requirements

        return [
            f"REPAIR: {error.error_type.value}"
            for error in errors
        ]


class FakeSQLValidator:

    def validate(self, sql, schemas):

        class Result:
            is_valid = True
            errors = []

        return Result()


class FakeSemanticValidator:

    def validate(
        self,
        question,
        sql,
        metrics_used,
    ):

        return {
            "is_valid": True,
            "errors": [],
        }


class FakeContextValidator:

    def __init__(self):
        self.sql = None
        self.requirements = None
        self.schemas = None

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        self.sql = sql
        self.requirements = requirements
        self.schemas = schemas

        return ContextValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
        )


class FailingContextValidator:

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        return ContextValidationResult(
            is_valid=False,
            errors=[
                "Expected DESC ordering but found ASC.",
            ],
            warnings=[],
        )


class RepairLoopSQLGenerator:

    def __init__(self):
        self.generate_calls = 0
        self.fix_calls = 0
        self.received_repairs = []

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.generate_calls += 1

        class Result:
            sql = (
                "SELECT name, "
                "SUM(quantity * unit_price) AS revenue "
                "FROM products "
                "GROUP BY name "
                "ORDER BY revenue ASC "
                "LIMIT 10"
            )

            metrics_used = ["revenue"]
            tables_used = ["products"]
            explanation = "Initial intentionally invalid SQL"

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_calls += 1
        self.received_repairs.append(errors)

        return (
            "SELECT name, "
            "SUM(quantity * unit_price) AS revenue "
            "FROM products "
            "GROUP BY name "
            "ORDER BY revenue DESC "
            "LIMIT 5"
        )


class RepairLoopContextValidator:

    def __init__(self):
        self.calls = 0
        self.sql_history = []
        self.requirements_history = []

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        self.calls += 1

        self.sql_history.append(sql)
        self.requirements_history.append(requirements)

        if self.calls == 1:

            return ContextValidationResult(
                is_valid=False,
                errors=[
                    "Expected DESC ordering but found ASC.",
                    "Expected LIMIT 5 but found LIMIT 10.",
                ],
                warnings=[],
            )

        return ContextValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
        )


class AlwaysFailingSQLGenerator:

    def __init__(self):
        self.generate_calls = 0
        self.fix_calls = 0
        self.fix_errors = []

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.generate_calls += 1

        class Result:
            sql = "SELECT invalid_sql"
            metrics_used = ["revenue"]
            tables_used = ["products"]
            explanation = "Intentionally invalid SQL"

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_calls += 1
        self.fix_errors.append(errors)

        # Deliberately return SQL that will continue to fail.
        return "SELECT invalid_sql"


class RepairFailingSQLGenerator:

    def __init__(self):
        self.generate_calls = 0
        self.fix_calls = 0

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.generate_calls += 1

        class Result:
            sql = "SELECT intentionally_invalid"
            metrics_used = ["revenue"]
            tables_used = ["products"]
            explanation = "Initial SQL"

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_calls += 1

        raise RuntimeError(
            "LLM repair service unavailable"
        )


class InitialGenerationFailingSQLGenerator:

    def __init__(self):
        self.generate_calls = 0
        self.fix_calls = 0

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.generate_calls += 1

        raise RuntimeError(
            "LLM generation service unavailable"
        )

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema,
        metadata,
        analytical_context=None,
    ):

        self.fix_calls += 1

        raise AssertionError(
            "fix_sql() must not be called when initial generation fails"
        )


class RepairFailureContextValidator:

    def __init__(self):
        self.calls = 0

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        self.calls += 1

        return ContextValidationResult(
            is_valid=False,
            errors=[
                "Expected DESC ordering but found ASC.",
            ],
            warnings=[],
        )


class AlwaysFailingContextValidator:

    def __init__(self):
        self.calls = 0

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        self.calls += 1

        return ContextValidationResult(
            is_valid=False,
            errors=[
                "Expected DESC ordering but found ASC.",
            ],
            warnings=[],
        )


class FakeDatabase:

    def validate_with_database(self, sql):

        return {
            "valid": True,
            "error": None,
        }


class MultipleErrorContextValidator:

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):

        return ContextValidationResult(
            is_valid=False,
            errors=[
                "Expected DESC ordering but found ASC.",
                "Expected LIMIT 5 but found LIMIT 10.",
            ],
            warnings=[],
        )


def create_sql_agent():

    generator = FakeSQLGenerator()

    context_validator = FakeContextValidator()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
    )

    return agent, generator


def create_state(context=None):

    metadata = MetadataResult(
        schemas=[
            {
                "table": "products",
                "columns": [
                    {
                        "name": "id",
                        "type": "integer",
                    },
                    {
                        "name": "name",
                        "type": "text",
                    },
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
            }
        ],
        schema_text="products(id, name)",
        metadata="product metadata",
    )

    return AgentState(
        question="Show top 5 products by revenue",
        metadata=metadata,
        analytical_context=context,
    )


def test_sql_agent_passes_analytical_context_to_generator():

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    agent, generator = create_sql_agent()

    state = create_state(context)

    result = agent.run(state)

    assert result.sql is not None
    assert result.sql.success is True

    assert generator.generate_context is context


def test_sql_agent_works_without_analytical_context():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.sql is not None
    assert result.sql.success is True

    assert generator.generate_context is None


def test_sql_agent_uses_targeted_repair_strategy():

    generator = RepairTrackingSQLGenerator()
    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=FailingContextValidator(),
        repair_strategy=repair_strategy,
        max_retries=2,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    assert result.sql is not None
    assert result.sql.success is False

    # ---------------------------------------------------------
    # Verify that SQLAgent called the repair strategy
    # ---------------------------------------------------------

    assert repair_strategy.received_errors is not None
    assert len(repair_strategy.received_errors) == 1

    assert (
        repair_strategy.received_errors[0].error_type
        == SQLErrorType.CONTEXT
    )

    # ---------------------------------------------------------
    # Verify that AnalyticalContext was passed to
    # the repair strategy
    # ---------------------------------------------------------

    assert repair_strategy.received_context is context

    # ---------------------------------------------------------
    # Verify that SQLRequirements were passed to
    # the repair strategy
    # ---------------------------------------------------------

    assert repair_strategy.received_requirements is not None

    requirements = repair_strategy.received_requirements

    assert requirements.entity == "product"
    assert requirements.metric == "revenue"
    assert requirements.aggregation == "sum"
    assert requirements.limit == 5
    assert requirements.sort_direction == "desc"

    # ---------------------------------------------------------
    # Verify that generated repair instructions were
    # passed to SQLGenerator.fix_sql()
    # ---------------------------------------------------------

    assert generator.fix_errors is not None

    assert generator.fix_errors == [
        "REPAIR: context",
    ]


def test_sql_agent_repairs_and_revalidates_until_success():

    generator = RepairLoopSQLGenerator()

    context_validator = RepairLoopContextValidator()

    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=2,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    # ---------------------------------------------------------
    # Final SQL must succeed
    # ---------------------------------------------------------

    assert result.sql is not None
    assert result.sql.success is True

    assert result.sql.sql is not None

    assert "ORDER BY revenue DESC" in result.sql.sql
    assert "LIMIT 5" in result.sql.sql

    # ---------------------------------------------------------
    # Generator should generate once and repair once
    # ---------------------------------------------------------

    assert generator.generate_calls == 1
    assert generator.fix_calls == 1

    # ---------------------------------------------------------
    # Context validator must run twice
    #
    # Attempt 1 -> failure
    # Attempt 2 -> success
    # ---------------------------------------------------------

    assert context_validator.calls == 2

    # ---------------------------------------------------------
    # First SQL should be the intentionally invalid SQL
    # ---------------------------------------------------------

    assert "ORDER BY revenue ASC" in (
        context_validator.sql_history[0]
    )

    assert "LIMIT 10" in (
        context_validator.sql_history[0]
    )

    # ---------------------------------------------------------
    # Second SQL should be the repaired SQL
    # ---------------------------------------------------------

    assert "ORDER BY revenue DESC" in (
        context_validator.sql_history[1]
    )

    assert "LIMIT 5" in (
        context_validator.sql_history[1]
    )

    # ---------------------------------------------------------
    # Repair strategy must have received both context errors
    # ---------------------------------------------------------

    assert repair_strategy.received_errors is not None

    assert len(repair_strategy.received_errors) == 2

    assert all(
        error.error_type == SQLErrorType.CONTEXT
        for error in repair_strategy.received_errors
    )

    # ---------------------------------------------------------
    # Analytical context must reach the repair strategy
    # ---------------------------------------------------------

    assert repair_strategy.received_context is context

    # ---------------------------------------------------------
    # SQL requirements must reach the repair strategy
    # ---------------------------------------------------------

    assert repair_strategy.received_requirements is not None

    requirements = repair_strategy.received_requirements

    assert requirements.entity == "product"
    assert requirements.metric == "revenue"
    assert requirements.aggregation == "sum"
    assert requirements.limit == 5
    assert requirements.sort_direction == "desc"

    # ---------------------------------------------------------
    # Repair instructions must reach SQLGenerator.fix_sql()
    # ---------------------------------------------------------

    assert generator.received_repairs

    assert len(generator.received_repairs) == 1

    assert generator.received_repairs[0] == [
        "REPAIR: context",
        "REPAIR: context",
    ]


def test_sql_agent_stops_after_max_retries():

    generator = AlwaysFailingSQLGenerator()
    context_validator = AlwaysFailingContextValidator()
    repair_strategy = FakeRepairStrategy()

    max_retries = 3

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=max_retries,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    # ---------------------------------------------------------
    # Final result must be a failure
    # ---------------------------------------------------------

    assert result.sql is not None
    assert result.sql.success is False

    # ---------------------------------------------------------
    # Exactly max_retries validation attempts
    # ---------------------------------------------------------

    assert context_validator.calls == max_retries

    # ---------------------------------------------------------
    # Initial generation happens exactly once
    # ---------------------------------------------------------

    assert generator.generate_calls == 1

    # ---------------------------------------------------------
    # Repair happens only between attempts.
    #
    # With 3 attempts:
    #
    # Attempt 1 -> repair
    # Attempt 2 -> repair
    # Attempt 3 -> stop
    # ---------------------------------------------------------

    assert generator.fix_calls == max_retries - 1

    # ---------------------------------------------------------
    # Final SQL must be the SQL from the final failed attempt
    # ---------------------------------------------------------

    assert result.sql.sql == "SELECT invalid_sql"

    # ---------------------------------------------------------
    # Attempt count must equal max_retries
    # ---------------------------------------------------------

    assert result.sql.attempts == max_retries

    # ---------------------------------------------------------
    # Errors must be preserved
    # ---------------------------------------------------------

    assert result.sql.errors is not None

    assert len(result.sql.errors) == max_retries

    assert all(
        "Expected DESC ordering but found ASC."
        in error
        for error in result.sql.errors
    )

    # ---------------------------------------------------------
    # Repair strategy must have been invoked
    # ---------------------------------------------------------

    assert repair_strategy.received_errors is not None

    assert len(repair_strategy.received_errors) == 1

    assert (
        repair_strategy.received_errors[0].error_type
        == SQLErrorType.CONTEXT
    )


def test_sql_agent_preserves_multiple_validation_errors():

    generator = AlwaysFailingSQLGenerator()
    context_validator = MultipleErrorContextValidator()
    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=1,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    assert result.sql is not None
    assert result.sql.success is False

    assert result.sql.attempts == 1

    assert len(result.sql.errors) == 2

    assert (
        "Expected DESC ordering but found ASC."
        in result.sql.errors
    )

    assert (
        "Expected LIMIT 5 but found LIMIT 10."
        in result.sql.errors
    )

    # No repair should happen because the only attempt
    # was already the final attempt.
    assert generator.fix_calls == 0

    # Both errors must reach the repair strategy even though
    # no LLM repair is performed after the final attempt.
    assert repair_strategy.received_errors is not None
    assert len(repair_strategy.received_errors) == 2


def test_sql_agent_handles_repair_failure():

    generator = RepairFailingSQLGenerator()

    context_validator = RepairFailureContextValidator()

    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=3,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    assert result.sql is not None

    assert result.sql.success is False

    # Initial SQL generation should happen exactly once.
    assert generator.generate_calls == 1

    # Repair should be attempted once.
    assert generator.fix_calls == 1

    # Validation should happen once before the repair fails.
    assert context_validator.calls == 1

    # The SQL that caused the repair attempt should be preserved.
    assert result.sql.sql == "SELECT intentionally_invalid"

    # The failure should contain the repair exception.
    assert result.sql.errors is not None

    assert any(
        "LLM repair service unavailable" in error
        for error in result.sql.errors
    )

    # The repair failure should also be present in the trace.
    assert result.execution_trace

    repair_events = [
        event
        for event in result.execution_trace
        if event["stage"] == "repair"
    ]

    assert len(repair_events) == 1
    assert repair_events[0]["status"] == "failed"
    assert repair_events[0]["error_type"] == "repair"

    assert repair_events[0]["metadata"][
        "repair_strategy"
    ] == "FakeRepairStrategy"

    assert repair_events[0]["metadata"][
        "exception_type"
    ] == "RuntimeError"


def test_sql_agent_handles_initial_generation_failure():

    generator = InitialGenerationFailingSQLGenerator()

    context_validator = FakeContextValidator()

    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=3,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    # The agent itself should return a failed state.
    assert result.success is False

    # SQLResult should exist and represent generation failure.
    assert result.sql is not None
    assert result.sql.success is False

    # No SQL was generated.
    assert result.sql.sql is None

    # No validation attempt happened.
    assert result.sql.attempts == 0

    # Initial generation was attempted exactly once.
    assert generator.generate_calls == 1

    # Repair must never happen because initial generation failed.
    assert generator.fix_calls == 0

    # The failure should identify the generation problem.
    assert result.sql.errors is not None

    assert any(
        "LLM generation service unavailable" in error
        for error in result.sql.errors
    )

    assert any(
        "SQL generation failed" in error
        for error in result.sql.errors
    )

    # There should be no trace because generation itself failed
    # before the trace could record a successful generation event.
    assert result.execution_trace == []


def test_sql_agent_records_execution_trace():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.success is True

    assert len(result.execution_trace) == 5

    stages = [
        event["stage"]
        for event in result.execution_trace
    ]

    assert stages == [
        "generation",
        "sqlglot_validation",
        "database_validation",
        "semantic_validation",
        "context_validation",
    ]


def test_sql_agent_execution_trace_contains_success_statuses():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.success is True

    for event in result.execution_trace:
        assert event["status"] == "success"


def test_sql_agent_execution_trace_records_repair():

    generator = RepairLoopSQLGenerator()

    context_validator = RepairLoopContextValidator()

    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        repair_strategy=repair_strategy,
        max_retries=2,
    )

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
    )

    state = create_state(context)

    result = agent.run(state)

    assert result.success is True

    repair_events = [
        event
        for event in result.execution_trace
        if event["stage"] == "repair"
    ]

    assert len(repair_events) == 1

    assert repair_events[0]["status"] == "success"

    assert repair_events[0]["attempt"] == 1

def test_sql_agent_execution_trace_events_follow_standard_schema():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.success is True

    assert result.execution_trace

    for event in result.execution_trace:

        validated_event = ExecutionTraceEvent(
            **event
        )

        assert validated_event.stage
        assert validated_event.status
        assert validated_event.attempt >= 0
        assert isinstance(
            validated_event.metadata,
            dict,
        )

def test_sql_agent_trace_contains_generation_metadata():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.success is True

    generation_event = next(
        event
        for event in result.execution_trace
        if event["stage"] == "generation"
    )

    assert generation_event["status"] == "success"
    assert generation_event["metadata"]["component"] == (
        "FakeSQLGenerator"
    )

def test_sql_agent_trace_contains_validation_metadata():

    agent, generator = create_sql_agent()

    state = create_state()

    result = agent.run(state)

    assert result.success is True

    events = {
        event["stage"]: event
        for event in result.execution_trace
    }

    assert events["sqlglot_validation"]["metadata"][
        "validator"
    ] == "FakeSQLValidator"

    assert events["database_validation"]["metadata"][
        "validator"
    ] == "FakeDatabase"

    assert events["semantic_validation"]["metadata"][
        "validator"
    ] == "FakeSemanticValidator"

    assert events["context_validation"]["metadata"][
        "validator"
    ] == "FakeContextValidator"

def test_sql_agent_trace_contains_context_error_metadata():

    generator = RepairTrackingSQLGenerator()

    repair_strategy = FakeRepairStrategy()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=FailingContextValidator(),
        repair_strategy=repair_strategy,
        max_retries=1,
    )

    state = create_state(
        AnalyticalContext(
            entity="product",
            metric="revenue",
            aggregation="sum",
            limit=5,
            sort_direction="desc",
        )
    )

    result = agent.run(state)

    assert result.success is False

    context_event = next(
        event
        for event in result.execution_trace
        if event["stage"] == "context_validation"
    )

    assert context_event["status"] == "failed"
    assert context_event["error_type"] == "context"
    assert context_event["metadata"]["validator"] == (
        "FailingContextValidator"
    )
    assert context_event["metadata"]["error_count"] == 1

