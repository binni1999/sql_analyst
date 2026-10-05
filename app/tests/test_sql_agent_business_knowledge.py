from agents.sql_agent import SQLAgent
from models.agent import MetadataResult
from models.business_knowledge import (
    BusinessKnowledgeDocument,
    BusinessKnowledgeMatch,
    BusinessKnowledgeResult,
)
from models.state import AgentState


class FakeGenerator:
    def __init__(self):
        self.received = None

    def generate(self, question, schema, metadata, analytical_context=None, business_knowledge=None):
        self.received = business_knowledge
        class Result:
            sql = "SELECT 1"
            metrics_used = []
            tables_used = []
            explanation = "test"
        return Result()

    def fix_sql(self, *args, **kwargs):
        return "SELECT 1"


class ValidSQLValidator:
    def validate(self, sql, schemas):
        class Result:
            is_valid = True
            errors = []
        return Result()


class ValidSemanticValidator:
    def validate(self, question, sql, metrics_used):
        return {"is_valid": True, "errors": []}


class ValidContextValidator:
    def validate(self, sql, requirements, schemas=None):
        from models.context_validation import ContextValidationResult
        return ContextValidationResult(is_valid=True, errors=[], warnings=[])


def test_sql_agent_forwards_business_knowledge_to_generator():
    generator = FakeGenerator()
    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=ValidSQLValidator(),
        semantic_validator=ValidSemanticValidator(),
        db=None,
        context_validator=ValidContextValidator(),
    )

    document = BusinessKnowledgeDocument(
        document_id="metric.revenue",
        title="Revenue",
        content="Revenue formula: SUM(quantity * unit_price * (1 - discount))",
        source="test",
    )
    knowledge = BusinessKnowledgeResult(
        query="revenue",
        matches=[
            BusinessKnowledgeMatch(
                document=document,
                score=1.0,
                matched_keywords=["revenue"],
            )
        ],
    )

    state = AgentState(
        question="Show revenue",
        metadata=MetadataResult(
            schemas=[],
            schema_text="TEST SCHEMA",
            metadata="TEST METADATA",
        ),
        business_knowledge=knowledge,
    )

    result = agent.run(state)

    print("SUCCESS:", result.success)
    print("ERROR:", result.error)
    print("CURRENT STEP:", result.current_step)
    print("SQL:", result.sql)
    print("TRACE:", result.execution_trace)

    assert result.success is True
    assert generator.received is knowledge
