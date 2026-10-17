from types import SimpleNamespace
from uuid import uuid4

from graph.nodes import answer_node, sql_node
from models.agent import AnalyticsResult, SQLResult
from models.state import AgentState
from services.observability import ObservabilityService


def record_fake_llm_call(handler):
    run_id = uuid4()

    handler.on_llm_start(
        serialized={
            "name": "fake-model",
            "kwargs": {"model": "fake-model"},
        },
        prompts=["Test prompt"],
        run_id=run_id,
    )

    handler.on_llm_end(
        response=SimpleNamespace(
            llm_output={
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                }
            }
        ),
        run_id=run_id,
        model="fake-model",
    )


def test_sql_node_attributes_llm_call_to_sql_agent_stage():
    service = ObservabilityService()
    state = AgentState(
        question="Show the top 5 products by revenue",
        sql=SQLResult(success=True, sql="SELECT 1"),
    )

    class FakeSQLAgent:
        def run(self, agent_state):
            record_fake_llm_call(service.callback_handler)
            return agent_state

    with service.capture(
        conversation_id="sql-stage-test"
    ) as context:
        result = sql_node(
            {"agent_state": state},
            FakeSQLAgent(),
        )

    assert result["agent_state"].sql.success is True
    assert len(context.llm_calls) == 1
    assert context.llm_calls[0].stage == "sql_agent"
    assert context.llm_calls[0].input_tokens == 10
    assert context.llm_calls[0].output_tokens == 5


def test_answer_node_attributes_llm_call_to_answer_generation_stage():
    service = ObservabilityService()
    state = AgentState(
        question="Show the top 5 products by revenue",
        sql=SQLResult(success=True, sql="SELECT 1"),
        analytics=AnalyticsResult(
            success=True,
            analysis={
                "columns": ["product_name"],
                "rows": [["Bike"]],
            },
        ),
    )

    class FakeAnswerGenerator:
        def generate(self, question, analyzed_result):
            record_fake_llm_call(service.callback_handler)
            return "The top product is Bike."

    with service.capture(
        conversation_id="answer-stage-test"
    ) as context:
        result = answer_node(
            {"agent_state": state},
            FakeAnswerGenerator(),
        )

    assert result["agent_state"].answer == "The top product is Bike."
    assert len(context.llm_calls) == 1
    assert context.llm_calls[0].stage == "answer_generation"
    assert context.llm_calls[0].input_tokens == 10
    assert context.llm_calls[0].output_tokens == 5



def test_tool_calling_llm_is_attributed_to_sql_agent_stage():
    from langchain_core.tools import StructuredTool
    # pyrefly: ignore [missing-import]
    from tools.sql_tool import ToolCallingExecutor

    service = ObservabilityService()

    tool = StructuredTool.from_function(
        lambda: {"schema": "orders"},
        name="get_schema",
        description="Return the database schema.",
    )

    class FakeResponse:
        def __init__(self, tool_calls=None):
            self.tool_calls = tool_calls or []
            self.content = "Discovery complete"

    class FakeToolModel:
        def __init__(self):
            self.calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            self.calls += 1

            # Simulate the model's configured observability callback.
            record_fake_llm_call(service.callback_handler)

            if self.calls == 1:
                return FakeResponse([
                    {
                        "name": "get_schema",
                        "args": {},
                        "id": "schema-call-1",
                    }
                ])

            return FakeResponse()

    model = FakeToolModel()
    executor = ToolCallingExecutor([tool], max_retries=0)

    with service.capture(
        conversation_id="tool-calling-observability-test"
    ) as context:
        with context.stage("sql_agent"):
            executor.run(
                model,
                [("human", "Retrieve the schema")],
            )

    assert model.calls == 2
    assert len(context.llm_calls) == 2
    assert all(
        call.stage == "sql_agent"
        for call in context.llm_calls
    )
    assert all(
        call.input_tokens == 10
        and call.output_tokens == 5
        for call in context.llm_calls
    )

