
from langchain_core.tools import StructuredTool

from agents.sql_agent import SQLAgent
from models.agent import MetadataResult
from models.state import AgentState
from tools.sql_tool import ToolCallingExecutor


class FakeGenerated:
    sql = "SELECT 1"
    metrics_used = []
    tables_used = []
    explanation = "test"


class FakeGenerator:
    def __init__(self):
        self.llm = FakeModel()

    def generate(self, *args, **kwargs):
        return FakeGenerated()


class FakeValidator:
    def validate(self, sql, schemas):
        class Result:
            is_valid = True
            errors = []
            warnings = []
        return Result()


class FakeSemanticValidator:
    def validate(self, question, sql, metrics_used):
        return {"is_valid": True, "errors": []}


class FakeDatabase:
    def validate_with_database(self, sql):
        return {"valid": True, "error": None}


class FakeContextValidator:
    def validate(self, sql, requirements, schemas=None):
        from models.context_validation import ContextValidationResult
        return ContextValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
        )


class FakeModel:
    def __init__(self):
        self.calls = 0
        self.messages = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.calls += 1
        self.messages = list(messages)

        class Response:
            def __init__(self, tool_calls):
                self.tool_calls = tool_calls
                self.content = "discovery complete"

        if self.calls == 1:
            return Response([
                {
                    "name": "get_metadata",
                    "args": {},
                    "id": "call-1",
                }
            ])

        return Response([])


def make_agent(tool_executor=None, tool_model=None):
    generator = FakeGenerator()
    return SQLAgent(
        sql_generator=generator,
        sql_validator=FakeValidator(),
        semantic_validator=FakeSemanticValidator(),
        db=FakeDatabase(),
        context_validator=FakeContextValidator(),
        tool_executor=tool_executor,
        tool_model=tool_model,
    )


def make_state():
    return AgentState(
        question="Show revenue",
        metadata=MetadataResult(
            schemas=[
                {
                    "table": "orders",
                    "columns": [
                        {"name": "id", "type": "integer"},
                    ],
                    "primary_keys": ["id"],
                    "foreign_keys": [],
                }
            ],
            schema_text="orders(id integer)",
            metadata="revenue: sales value",
        ),
    )


def test_sql_agent_uses_llm_selected_tool_before_generation():
    tool_calls = []

    def get_metadata():
        tool_calls.append("get_metadata")
        return {"metrics": {"revenue": {"description": "sales"}}}

    tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )

    model = FakeModel()
    executor = ToolCallingExecutor([tool], max_retries=0)

    agent = make_agent(
        tool_executor=executor,
        tool_model=model,
    )

    result = agent.run(make_state())

    assert result.success is True
    assert tool_calls == ["get_metadata"]
    assert model.calls == 2

    tool_events = [
        event for event in result.execution_trace
        if event["stage"] == "tool_call"
    ]

    assert len(tool_events) == 1
    assert tool_events[0]["status"] == "success"
    assert tool_events[0]["metadata"]["tool"] == "get_metadata"


def test_sql_agent_does_not_call_tools_when_tool_capability_is_not_configured():
    agent = make_agent()

    result = agent.run(make_state())

    assert result.success is True
    assert all(event["stage"] != "tool_call" for event in result.execution_trace)


def test_sql_agent_falls_back_when_optional_validation_tool_is_not_configured():
    tool = StructuredTool.from_function(
        lambda: {"ok": True},
        name="get_metadata",
        description="Metadata tool only.",
    )
    executor = ToolCallingExecutor([tool], max_retries=0)
    agent = make_agent(tool_executor=executor, tool_model=FakeModel())

    result = agent.run(make_state())

    assert result.success is True
    assert not any(
        event.get("message", "").startswith("SQL validation tool failed")
        for event in result.execution_trace
    )



def test_sql_agent_allows_two_discovery_tool_rounds():
    tool_calls = []

    def get_metadata():
        tool_calls.append("get_metadata")
        return {"metrics": {"revenue": {"description": "sales"}}}

    tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )

    class TwoRoundFakeModel(FakeModel):
        def invoke(self, messages):
            self.calls += 1
            self.messages = list(messages)

            class Response:
                def __init__(self, tool_calls):
                    self.tool_calls = tool_calls
                    self.content = "discovery complete"

            if self.calls <= 2:
                return Response([
                    {
                        "name": "get_metadata",
                        "args": {},
                        "id": f"call-{self.calls}",
                    }
                ])

            return Response([])

    model = TwoRoundFakeModel()
    executor = ToolCallingExecutor(
        [tool],
        max_retries=0,
        max_tool_rounds=5,
    )
    agent = make_agent(
        tool_executor=executor,
        tool_model=model,
    )

    result = agent.run(make_state())

    assert result.success is True
    assert tool_calls == ["get_metadata", "get_metadata"]
    assert model.calls == 3
    assert not any(
        event.get("metadata", {}).get("fallback")
        == "deterministic_metadata_schema"
        for event in result.execution_trace
    )



def test_sql_agent_falls_back_when_discovery_exceeds_round_limit():
    tool_calls = []

    def get_metadata():
        tool_calls.append("get_metadata")
        return {"metrics": {"revenue": {"description": "sales"}}}

    tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )

    class EndlessToolCallModel(FakeModel):
        def invoke(self, messages):
            self.calls += 1
            self.messages = list(messages)

            class Response:
                content = "Continue discovery"

                def __init__(self, calls):
                    self.tool_calls = calls

            return Response([
                {
                    "name": "get_metadata",
                    "args": {},
                    "id": f"call-{self.calls}",
                }
            ])

    model = EndlessToolCallModel()
    executor = ToolCallingExecutor(
        [tool],
        max_retries=0,
        max_tool_rounds=5,
    )
    agent = make_agent(
        tool_executor=executor,
        tool_model=model,
    )

    result = agent.run(make_state())

    assert result.success is True
    assert model.calls == 3
    assert len(tool_calls) == 3

    fallback_events = [
        event
        for event in result.execution_trace
        if event.get("metadata", {}).get("fallback")
        == "deterministic_metadata_schema"
    ]
    assert len(fallback_events) == 1
    assert fallback_events[0]["status"] == "failed"


def test_sql_agent_falls_back_when_validate_sql_tool_raises():
    from langchain_core.tools import StructuredTool

    def get_metadata():
        return {"metrics": {"revenue": {"description": "sales"}}}

    def validate_sql(sql: str):
        raise RuntimeError("validation tool unavailable")

    metadata_tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )

    validation_tool = StructuredTool.from_function(
        validate_sql,
        name="validate_sql",
        description="Validate SQL.",
    )

    executor = ToolCallingExecutor(
        [metadata_tool, validation_tool],
        max_retries=0,
    )

    agent = make_agent(
        tool_executor=executor,
        tool_model=FakeModel(),
    )

    result = agent.run(make_state())

    assert result.success is True

    failure_events = [
        event
        for event in result.execution_trace
        if event.get("stage") == "tool_call"
        and event.get("status") == "failed"
        and "validate_sql tool failed" in event.get("message", "")
    ]

    assert len(failure_events) == 1
    assert failure_events[0]["error_type"] == "tool"
    assert failure_events[0]["metadata"]["tool"] == "validate_sql"
    assert (
        failure_events[0]["metadata"]["fallback"]
        == "deterministic_validation"
    )



def test_sql_agent_falls_back_when_repair_sql_tool_raises():
    from models.context_validation import ContextValidationResult

    def get_metadata():
        return {"metrics": {"revenue": {"description": "sales"}}}

    def repair_sql(
        question: str,
        sql: str,
        errors: list[str],
        analytical_context: dict | None = None,
        business_knowledge: dict | None = None,
    ):
        raise RuntimeError("repair tool unavailable")

    class FailingContextValidator:
        def validate(self, sql, requirements, schemas=None):
            return ContextValidationResult(
                is_valid=False,
                errors=["Missing required analytical context"],
                warnings=[],
            )

    class RepairTrackingGenerator(FakeGenerator):
        def __init__(self):
            super().__init__()
            self.fix_calls = 0

        def fix_sql(self, *args, **kwargs):
            self.fix_calls += 1
            return "SELECT 1"

    metadata_tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )
    repair_tool = StructuredTool.from_function(
        repair_sql,
        name="repair_sql",
        description="Repair SQL.",
    )

    executor = ToolCallingExecutor(
        [metadata_tool, repair_tool],
        max_retries=0,
    )

    generator = RepairTrackingGenerator()
    agent = make_agent(
        tool_executor=executor,
        tool_model=FakeModel(),
    )
    agent.sql_generator = generator
    agent.context_validator = FailingContextValidator()

    result = agent.run(make_state())

    repair_events = [
        event
        for event in result.execution_trace
        if event.get("stage") == "tool_call"
        and event.get("status") == "failed"
        and "repair_sql tool failed" in event.get("message", "")
    ]

    assert len(repair_events) >= 1
    assert repair_events[0]["error_type"] == "tool"
    assert repair_events[0]["metadata"]["tool"] == "repair_sql"
    assert repair_events[0]["metadata"]["fallback"] == "sql_generator"
    assert generator.fix_calls >= 1


def test_sql_agent_skips_discovery_when_no_allowed_tools_exist():
    unrelated_tool = StructuredTool.from_function(
        lambda: {"ok": True},
        name="unrelated_tool",
        description="A tool not allowed during SQL discovery.",
    )

    executor = ToolCallingExecutor(
        [unrelated_tool],
        max_retries=0,
    )
    model = FakeModel()

    agent = make_agent(
        tool_executor=executor,
        tool_model=model,
    )

    result = agent.run(make_state())

    assert result.success is True
    assert model.calls == 0
    assert not any(
        event["stage"] == "tool_call"
        for event in result.execution_trace
    )


def test_sql_agent_includes_business_knowledge_in_discovery_context():
    from models.business_knowledge import (
        BusinessKnowledgeDocument,
        BusinessKnowledgeMatch,
        BusinessKnowledgeResult,
    )

    tool_calls = []

    def get_metadata():
        tool_calls.append("get_metadata")
        return {"metrics": {"revenue": {"description": "sales"}}}

    tool = StructuredTool.from_function(
        get_metadata,
        name="get_metadata",
        description="Return business metric metadata.",
    )

    model = FakeModel()
    executor = ToolCallingExecutor([tool], max_retries=0)

    agent = make_agent(
        tool_executor=executor,
        tool_model=model,
    )

    knowledge = BusinessKnowledgeResult(
        query="revenue",
        matches=[
            BusinessKnowledgeMatch(
                document=BusinessKnowledgeDocument(
                    document_id="revenue-definition",
                    title="Revenue Definition",
                    content="Revenue equals quantity multiplied by unit price.",
                    source="business-glossary",
                ),
                score=0.95,
            )
        ],
    )

    agent._run_tool_discovery(
        question="Show revenue",
        analytical_context=None,
        business_knowledge=knowledge,
        execution_trace=[],
    )

    assert model.calls >= 1
    assert any(
        "Revenue Definition" in str(message)
        and "quantity multiplied by unit price" in str(message)
        for message in model.messages
    )
    assert tool_calls == ["get_metadata"]

def test_repair_sql_uses_generator_when_repair_tool_is_absent():
    agent = make_agent()

    calls = {}

    def fake_fix_sql(**kwargs):
        calls.update(kwargs)
        return "SELECT repaired"

    agent._fix_sql = fake_fix_sql

    result = agent._repair_sql(
        question="Show revenue",
        sql="SELECT invalid",
        errors=["Invalid SQL"],
        schema="orders(id integer)",
        metadata="revenue metadata",
        analytical_context=None,
        business_knowledge=None,
        execution_trace=[],
    )

    assert result == "SELECT repaired"
    assert calls["question"] == "Show revenue"
    assert calls["sql"] == "SELECT invalid"
    assert calls["errors"] == ["Invalid SQL"]
    assert calls["business_knowledge"] is None



def test_repair_sql_returns_successful_repair_tool_result():
    from langchain_core.tools import StructuredTool
    from tools.sql_tool import ToolCallingExecutor

    def repair_sql(
        question: str,
        sql: str,
        errors: list[str],
        analytical_context: dict | None = None,
        business_knowledge: dict | None = None,
    ) -> str:
        assert question == "Show revenue"
        assert sql == "SELECT invalid"
        assert errors == ["Invalid SQL"]
        return "SELECT repaired_by_tool"

    repair_tool = StructuredTool.from_function(
        repair_sql,
        name="repair_sql",
        description="Repair invalid SQL.",
    )

    executor = ToolCallingExecutor(
        [repair_tool],
        max_retries=0,
    )
    agent = make_agent(tool_executor=executor)

    fallback_calls = []

    def unexpected_fallback(**kwargs):
        fallback_calls.append(kwargs)
        return "SELECT fallback"

    agent._fix_sql = unexpected_fallback
    execution_trace = []

    result = agent._repair_sql(
        question="Show revenue",
        sql="SELECT invalid",
        errors=["Invalid SQL"],
        schema="orders(id integer)",
        metadata="revenue metadata",
        analytical_context=None,
        business_knowledge=None,
        execution_trace=execution_trace,
    )

    assert result == "SELECT repaired_by_tool"
    assert fallback_calls == []



def test_sql_agent_handles_exception_during_postgres_repair():
    class FailingDatabase:
        def validate_with_database(self, sql):
            return {
                "valid": False,
                "error": "PostgreSQL syntax validation failed",
            }

    agent = make_agent()
    agent.db = FailingDatabase()
    agent.max_retries = 2

    def fail_repair(**kwargs):
        raise RuntimeError("PostgreSQL repair failed")

    agent._repair_sql = fail_repair

    result = agent.run(make_state())

    assert result is not None
    assert result.success is False
    assert result.sql.errors
    assert any(
        "PostgreSQL syntax validation failed" in str(error)
        for error in result.sql.errors
    )



def test_sql_agent_handles_exception_during_semantic_repair():
    class FailingSemanticValidator:
        def validate(self, question, sql, metrics_used):
            return {
                "is_valid": False,
                "errors": ["Revenue formula is incorrect"],
            }

    agent = make_agent()
    agent.semantic_validator = FailingSemanticValidator()
    agent.max_retries = 2

    def fail_repair(**kwargs):
        raise RuntimeError("Semantic repair failed")

    agent._repair_sql = fail_repair

    result = agent.run(make_state())

    assert result is not None
    assert result.success is False
    assert result.sql.errors
    assert any(
        "Revenue formula is incorrect" in str(error)
        for error in result.sql.errors
    )
