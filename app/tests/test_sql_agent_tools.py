
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
