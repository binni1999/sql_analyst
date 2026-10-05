from models.analytical_context import AnalyticalContext
from models.agent import MetadataResult
from models.state import AgentState
from models.context_validation import ContextValidationResult

from agents.sql_agent import SQLAgent


# ============================================================
# FAKE SQL GENERATOR
# ============================================================

class FakeSQLGenerator:

    def __init__(self):
        self.generate_context = None
        self.fix_context = None
        self.fix_errors = None

    def generate(
        self,
        question,
        schema,
        metadata,
        analytical_context=None,
    ):
        self.generate_context = analytical_context

        class Result:
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
            """

            metrics_used = ["revenue"]
            tables_used = ["products", "order_items"]
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
        self.fix_errors = errors

        return sql


# ============================================================
# FAKE SQL VALIDATOR
# ============================================================

class FakeSQLValidator:

    def validate(self, sql, schemas):

        class Result:
            is_valid = True
            errors = []

        return Result()


# ============================================================
# FAKE SEMANTIC VALIDATOR
# ============================================================

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


# ============================================================
# FAKE DATABASE
# ============================================================

class FakeDatabase:

    def validate_with_database(self, sql):
        return {
            "valid": True,
            "error": None,
        }


# ============================================================
# FAKE CONTEXT VALIDATOR
# ============================================================

class FakeContextValidator:

    def __init__(self):
        self.requirements = None
        self.schemas = None

    def validate(
        self,
        sql,
        requirements,
        schemas=None,
    ):
        self.requirements = requirements
        self.schemas = schemas

        return ContextValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
        )


# ============================================================
# FAKE ERROR CLASSIFIER
# ============================================================

class FakeErrorClassifier:

    def __init__(self):
        self.called_with = None

    def classify(
        self,
        syntax_errors,
        database_errors,
        semantic_errors,
        context_errors,
    ):
        self.called_with = {
            "syntax_errors": syntax_errors,
            "database_errors": database_errors,
            "semantic_errors": semantic_errors,
            "context_errors": context_errors,
        }

        return [
            "classified error"
        ]


# ============================================================
# FAKE REPAIR STRATEGY
# ============================================================

class FakeRepairStrategy:

    def __init__(self):
        self.errors = None
        self.analytical_context = None
        self.requirements = None

    def build_instructions(
        self,
        errors,
        analytical_context=None,
        requirements=None,
    ):
        self.errors = errors
        self.analytical_context = analytical_context
        self.requirements = requirements

        return [
            "context-aware repair instruction"
        ]


# ============================================================
# TEST DATA
# ============================================================

def create_state(context=None):

    metadata = MetadataResult(
        schemas=[
            {
                "table": "products",
                "columns": [
                    {
                        "name": "product_id",
                        "type": "integer",
                    },
                    {
                        "name": "product_name",
                        "type": "text",
                    },
                ],
                "primary_keys": [
                    "product_id"
                ],
                "foreign_keys": [],
            },
            {
                "table": "order_items",
                "columns": [
                    {
                        "name": "product_id",
                        "type": "integer",
                    },
                    {
                        "name": "quantity",
                        "type": "integer",
                    },
                    {
                        "name": "unit_price",
                        "type": "numeric",
                    },
                    {
                        "name": "discount",
                        "type": "numeric",
                    },
                ],
                "primary_keys": [],
                "foreign_keys": [],
            },
        ],
        schema_text=(
            "products(product_id, product_name), "
            "order_items("
            "product_id, quantity, unit_price, discount"
            ")"
        ),
        metadata="product and order item metadata",
    )

    return AgentState(
        question="Show top 5 products by revenue",
        metadata=metadata,
        analytical_context=context,
    )


def create_sql_agent():

    generator = FakeSQLGenerator()
    error_classifier = FakeErrorClassifier()
    repair_strategy = FakeRepairStrategy()

    context_validator = FakeContextValidator()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=FakeSQLValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=context_validator,
        error_classifier=error_classifier,
        repair_strategy=repair_strategy,
    )

    return (
        agent,
        generator,
        error_classifier,
        repair_strategy,
        context_validator,
    )


# ============================================================
# TEST 1
# ============================================================

def test_sql_agent_passes_analytical_context_to_generator():

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="descending",
    )

    (
        agent,
        generator,
        _,
        _,
        _,
    ) = create_sql_agent()

    state = create_state(context)

    result = agent.run(state)

    assert result.sql is not None
    assert result.sql.success is True

    assert generator.generate_context is context


# ============================================================
# TEST 2
# ============================================================

def test_sql_agent_passes_context_and_requirements_to_repair_strategy():

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="descending",
    )

    (
        agent,
        generator,
        error_classifier,
        repair_strategy,
        context_validator,
    ) = create_sql_agent()

    # --------------------------------------------------------
    # Force ContextValidator to fail so that the repair path
    # is executed.
    # --------------------------------------------------------

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
                    "Expected LIMIT 5 but no LIMIT clause was found."
                ],
                warnings=[],
            )

    agent.context_validator = FailingContextValidator()

    state = create_state(context)

    result = agent.run(state)

    # --------------------------------------------------------
    # SQL generation should have received context.
    # --------------------------------------------------------

    assert generator.generate_context is context

    # --------------------------------------------------------
    # SQLRequirements should have been created.
    # --------------------------------------------------------

    assert repair_strategy.requirements is not None

    # --------------------------------------------------------
    # Repair strategy must receive the same AnalyticalContext.
    # --------------------------------------------------------

    assert (
        repair_strategy.analytical_context
        is context
    )

    # --------------------------------------------------------
    # Error classifier should have received the context
    # validation error.
    # --------------------------------------------------------

    assert (
        error_classifier.called_with[
            "context_errors"
        ]
        == [
            "Expected LIMIT 5 but no LIMIT clause was found."
        ]
    )

    # --------------------------------------------------------
    # Repair strategy should receive classified errors.
    # --------------------------------------------------------

    assert (
        repair_strategy.errors
        == ["classified error"]
    )


# ============================================================
# TEST 3
# ============================================================

def test_sql_agent_repair_instructions_are_passed_to_fix_sql():

    context = AnalyticalContext(
        entity="product",
        metric="quantity",
        aggregation="sum",
        limit=5,
        sort_direction="descending",
    )

    (
        agent,
        generator,
        _,
        _,
        _,
    ) = create_sql_agent()

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
                    "Expected descending ordering."
                ],
                warnings=[],
            )

    agent.context_validator = FailingContextValidator()

    state = create_state(context)

    agent.run(state)

    # --------------------------------------------------------
    # The repair strategy should have generated an instruction.
    # --------------------------------------------------------

    assert (
        generator.fix_errors
        == [
            "context-aware repair instruction"
        ]
    )

    # --------------------------------------------------------
    # The same AnalyticalContext must reach fix_sql().
    # --------------------------------------------------------

    assert (
        generator.fix_context
        is context
    )