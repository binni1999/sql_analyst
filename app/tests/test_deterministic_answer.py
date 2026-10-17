from graph.nodes import answer_node
from models.agent import AnalyticsResult
from models.state import AgentState
from services.deterministic_answer import build_deterministic_answer


def test_deterministic_answer_formats_actual_rows():
    answer = build_deterministic_answer({
        "columns": ["product_name", "revenue"],
        "rows": [["Bike", 12500], ["Laptop", 9800]],
    })

    assert answer is not None
    assert "product_name: Bike" in answer
    assert "revenue: 12500" in answer
    assert "product_name: Laptop" in answer


def test_deterministic_answer_limits_rows():
    answer = build_deterministic_answer({
        "columns": ["value"],
        "rows": [[i] for i in range(12)],
    })

    assert answer is not None
    assert "value: 9" in answer
    assert "2 additional row(s) not shown" in answer
    assert "value: 10" not in answer


def test_answer_node_uses_fallback_but_preserves_failure():
    state = AgentState(
        question="Show products",
        analytics=AnalyticsResult(
            success=True,
            analysis={
                "columns": ["product_name"],
                "rows": [["Bike"]],
            },
        ),
    )

    class FailingAnswerGenerator:
        def generate(self, question, analyzed_result):
            raise RuntimeError("simulated provider failure")

    result = answer_node(
        {"agent_state": state},
        FailingAnswerGenerator(),
    )
    updated = result["agent_state"]

    assert updated.answer is not None
    assert "product_name: Bike" in updated.answer
    assert updated.success is False
    assert "Answer generation failed" in str(updated.error)
    assert updated.execution_trace[-1]["stage"] == "answer_generation"
    assert updated.execution_trace[-1]["status"] == "failed"
    assert (
        updated.execution_trace[-1]["metadata"]["exception_type"]
        == "RuntimeError"
    )


def test_answer_node_does_not_fabricate_fallback_for_failed_analytics():
    state = AgentState(
        question="Show products",
        analytics=AnalyticsResult(
            success=False,
            analysis={
                "columns": ["product_name"],
                "rows": [["Bike"]],
            },
            error="Analytics execution failed",
        ),
    )

    class FailingAnswerGenerator:
        def generate(self, question, analyzed_result):
            raise RuntimeError("simulated provider failure")

    result = answer_node(
        {"agent_state": state},
        FailingAnswerGenerator(),
    )
    updated = result["agent_state"]

    assert updated.answer is None
    assert updated.success is False
    assert updated.execution_trace[-1]["status"] == "failed"


def test_answer_node_does_not_fabricate_fallback_when_analytics_missing():
    state = AgentState(question="Show products")

    class FailingAnswerGenerator:
        def generate(self, question, analyzed_result):
            raise AssertionError("Generator must not be called")

    result = answer_node(
        {"agent_state": state},
        FailingAnswerGenerator(),
    )

    assert result["agent_state"].answer is None
    assert result["agent_state"].success is False
