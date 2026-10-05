import json

import pytest
from langchain_core.tools import StructuredTool

from tools.sql_tool import (
    ToolCallError,
    ToolCallingExecutor,
    build_sql_tools,
)


class FakeDatabase:
    def get_schema(self, table_name):
        return {"table": table_name, "columns": []}

    def get_full_schema(self):
        return [{"table": "orders", "columns": [{"name": "id", "type": "integer"}]}]

    def validate_with_database(self, sql):
        return {"valid": sql == "SELECT 1", "error": None if sql == "SELECT 1" else "bad SQL"}



class FakeSecureExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, sql):
        self.calls.append(sql)
        if sql != "SELECT 1":
            raise ValueError("Only guarded SELECT queries are allowed.")
        return {"columns": ["1"], "rows": [[1]]}


class FakeMetadataService:
    def get_column_metadata(self):
        return {"orders": {"id": {"description": "Order id"}}}

    def get_metric_metadata(self):
        return {"count": {"description": "Number of rows"}}

    def build_metadata_text(self):
        return "orders.id: Order id"


class FakeValidator:
    def validate(self, sql, schemas):
        class Result:
            is_valid = sql == "SELECT 1"
            errors = [] if is_valid else ["syntax error"]
            warnings = []

        return Result()


class FakeGenerator:
    def fix_sql(self, **kwargs):
        return "SELECT 1"


def _tools():
    return build_sql_tools(
        db=FakeDatabase(),
        metadata_service=FakeMetadataService(),
        sql_validator=FakeValidator(),
        sql_generator=FakeGenerator(),
        secure_executor=FakeSecureExecutor(),
    )


def test_sql_tools_expose_structured_contracts_and_operations():
    tools = {tool.name: tool for tool in _tools()}

    assert set(tools) == {
        "get_schema",
        "get_metadata",
        "validate_sql",
        "execute_sql",
        "repair_sql",
    }
    assert tools["get_schema"].invoke({"table_name": "orders"})["table"] == "orders"
    assert tools["get_metadata"].invoke({})["metrics"]["count"]
    assert tools["validate_sql"].invoke({"sql": "SELECT 1"})["is_valid"] is True
    assert tools["execute_sql"].invoke({"sql": "SELECT 1"})["rows"] == [[1]]
    assert tools["repair_sql"].invoke({
        "question": "count orders",
        "sql": "bad",
        "errors": ["syntax error"],
    }) == "SELECT 1"


def test_executor_retries_tool_failure_and_records_trace():
    calls = {"count": 0}

    def sometimes_fails(value: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary")
        return value

    tool = StructuredTool.from_function(
        sometimes_fails,
        name="sometimes_fails",
        description="Return a value, failing once to exercise retry behavior.",
    )
    executor = ToolCallingExecutor([tool], max_retries=1)
    trace = []

    assert executor.execute("sometimes_fails", {"value": "ok"}, execution_trace=trace) == "ok"
    assert calls["count"] == 2
    assert [event["status"] for event in trace] == ["retrying", "success"]


def test_executor_returns_structured_failure_after_retry_limit():
    def always_fails() -> str:
        raise RuntimeError("unavailable")

    tool = StructuredTool.from_function(
        always_fails,
        name="always_fails",
        description="Always fail to exercise retry exhaustion.",
    )
    executor = ToolCallingExecutor([tool], max_retries=1)

    with pytest.raises(ToolCallError, match="failed after 2 attempt"):
        executor.execute("always_fails", {})


def test_executor_rejects_unknown_tool():
    executor = ToolCallingExecutor(_tools())

    with pytest.raises(ToolCallError, match="Unknown tool"):
        executor.execute("missing_tool", {})


def test_model_selects_tool_and_receives_result_before_final_response():
    class Response:
        def __init__(self, tool_calls=None, content="done"):
            self.tool_calls = tool_calls or []
            self.content = content

    class FakeModel:
        def __init__(self):
            self.calls = 0
            self.messages = None

        def bind_tools(self, tools):
            self.tools = tools
            return self

        def invoke(self, messages):
            self.calls += 1
            self.messages = messages
            if self.calls == 1:
                return Response([{
                    "name": "execute_sql",
                    "args": {"sql": "SELECT 1"},
                    "id": "call-1",
                }])
            return Response()

    model = FakeModel()
    executor = ToolCallingExecutor(_tools())

    response = executor.run(model, ["question"])

    assert response.content == "done"
    assert model.calls == 2
    tool_result = json.loads(model.messages[-1].content)
    assert tool_result["success"] is True
    assert tool_result["rows"] == [[1]]
