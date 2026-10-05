from evaluation.harness import EvaluationHarness
from evaluation.models import EvaluationCase, EvaluationDataset
from models.response import DataAnalystResponse


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def ask(self, question, *, conversation_id, human_approval=None):
        self.calls.append((question, conversation_id, human_approval))
        return self.responses[len(self.calls) - 1]


def _response(
    *,
    question="Show revenue",
    sql="SELECT SUM(quantity * unit_price * (1 - discount)) AS total_revenue FROM order_items",
    answer="Total revenue after discount is 100.",
    success=True,
    needs_clarification=False,
    needs_human_approval=False,
    trace=None,
):
    return DataAnalystResponse(
        success=success,
        question=question,
        conversation_id="ignored",
        answer=answer,
        sql=sql,
        result={"row_count": 1},
        needs_clarification=needs_clarification,
        needs_human_approval=needs_human_approval,
        execution_trace=trace or [],
    )


def test_harness_runs_a_case_and_combines_evaluators():
    case = EvaluationCase(
        case_id="case-1",
        category="revenue",
        description="Revenue",
        question="Show revenue",
        expected_sql=(
            "SELECT SUM(quantity * unit_price * (1 - discount)) "
            "AS total_revenue FROM order_items"
        ),
        expected_tables=["order_items"],
        expected_metric="revenue",
        expected_answer="Total revenue after discount.",
        expected_behavior={"outcome": "execute_query"},
    )
    dataset = EvaluationDataset(
        dataset_id="test",
        version="1.0.0",
        description="test",
        cases=[case],
    )
    runner = FakeRunner([
        _response(
            trace=[
                {"stage": "intent", "status": "success", "message": "Question classified as DATA_QUERY.", "metadata": {}},
                {"stage": "metadata", "status": "success", "message": "", "metadata": {}},
                {"stage": "business_knowledge", "status": "success", "message": "", "metadata": {"matched_document_ids": ["metric.revenue"]}},
                {"stage": "sql_agent", "status": "success", "message": "", "metadata": {}},
            ]
        )
    ])

    summary = EvaluationHarness(runner).run_dataset(dataset)

    assert summary.evaluated_cases == 1
    assert summary.sql_evaluated_cases == 1
    assert summary.semantic_evaluated_cases == 1
    assert summary.answer_evaluated_cases == 1
    assert summary.behavior_evaluated_cases == 1
    assert summary.results[0].runtime.generated_sql is not None
    assert runner.calls[0][0] == "Show revenue"


def test_harness_preserves_cases_without_sql_ground_truth():
    case = EvaluationCase(
        case_id="clarification",
        category="clarification",
        description="Clarify",
        question="Show me the best products",
        expected_behavior={"outcome": "clarification", "clarification": True},
    )
    dataset = EvaluationDataset(
        dataset_id="test",
        version="1.0.0",
        description="test",
        cases=[case],
    )
    runner = FakeRunner([
        _response(
            answer=None,
            sql=None,
            success=True,
            needs_clarification=True,
            trace=[
                {"stage": "intent", "status": "success", "message": "Question classified as DATA_QUERY.", "metadata": {}},
                {"stage": "clarification", "status": "required", "message": "", "metadata": {}},
            ],
        )
    ])

    result = EvaluationHarness(runner).run_case(case)

    assert result.sql is not None
    assert result.sql.evaluated is False
    assert result.semantic is not None
    assert result.semantic.evaluated is False
    assert result.answer is not None
    assert result.answer.evaluated is False
    assert result.behavior["passed"] is True


def test_harness_uses_same_conversation_for_multiple_turns():
    case = EvaluationCase(
        case_id="multi",
        category="multi_turn",
        description="Multi turn",
        question="Show revenue",
        conversation=[
            {"question": "Show revenue"},
            {"question": "Only delivered orders"},
        ],
        expected_behavior={
            "outcome": "execute_query",
            "uses_memory": True,
            "uses_previous_context": True,
        },
    )
    dataset = EvaluationDataset(
        dataset_id="test",
        version="1.0.0",
        description="test",
        cases=[case],
    )
    runner = FakeRunner([
        _response(question="Show revenue"),
        _response(question="Only delivered orders"),
    ])

    result = EvaluationHarness(runner).run_case(case)

    assert result.runtime.turns_executed == 2
    assert runner.calls[0][1] == runner.calls[1][1]
    assert result.behavior["passed"] is True
