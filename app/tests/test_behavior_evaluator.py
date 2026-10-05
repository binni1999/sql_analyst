from evaluation.behavior_evaluator import (
    AgentBehaviorObservation,
    evaluate_agent_behavior,
    evaluate_agent_behaviors,
)
from evaluation.dataset import load_evaluation_dataset


def _trace(*stages):
    return [
        {"stage": stage, "status": "success", "metadata": {}}
        for stage in stages
    ]


def test_routing_accuracy_accepts_expected_route_with_trace_events():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "revenue-001")

    observation = AgentBehaviorObservation(
        outcome="execute_query",
        intent="data_query",
        route=[
            "intent",
            "clarification",
            "metadata",
            "business_knowledge",
            "sql",
            "risk_check",
            "analytics",
            "answer",
            "completed",
        ],
        execution_trace=_trace(
            "intent",
            "clarification",
            "metadata",
            "business_knowledge",
            "sql_agent",
            "risk_check",
            "analytics",
            "answer_generation",
            "completed",
        ),
        business_knowledge_document_ids=["metric.revenue"],
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["intent"] is True
    assert result.checks["routing"] is True
    assert result.checks["business_knowledge_documents"] is True


def test_tool_selection_requires_expected_tools():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "tool-001")

    trace = [
        {
            "stage": "tool_call",
            "status": "success",
            "metadata": {"tool": "get_schema"},
        },
        {
            "stage": "tool_call",
            "status": "success",
            "metadata": {"tool": "get_metadata"},
        },
    ]

    observation = AgentBehaviorObservation(
        outcome="execute_query",
        intent="data_query",
        tools_used=["get_schema", "get_metadata"],
        execution_trace=trace,
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["tool_selection"] is True


def test_clarification_behavior_is_evaluated():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "clarification-001")

    observation = AgentBehaviorObservation(
        outcome="clarification",
        intent="data_query",
        clarification_required=True,
        clarification_question="What metric do you mean?",
        execution_trace=[
            {
                "stage": "clarification",
                "status": "required",
                "metadata": {},
            }
        ],
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["clarification"] is True


def test_business_knowledge_usage_is_evaluated():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "business-001")

    observation = AgentBehaviorObservation(
        outcome="execute_query",
        intent="data_query",
        business_knowledge_document_ids=["metric.revenue"],
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["business_knowledge"] is True
    assert result.checks["business_knowledge_documents"] is True


def test_memory_and_previous_context_usage_are_evaluated():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "multiturn-001")

    observation = AgentBehaviorObservation(
        outcome="execute_query",
        memory_turn_count=2,
        used_previous_context=True,
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["memory"] is True
    assert result.checks["memory_store"] is True


def test_hitl_behavior_requires_approval_and_risk_type():
    dataset = load_evaluation_dataset()
    case = next(c for c in dataset.cases if c.case_id == "hitl-001")

    observation = AgentBehaviorObservation(
        outcome="human_approval",
        intent="data_query",
        human_approval_required=True,
        human_approval_status="pending",
        route=["intent", "metadata", "business_knowledge", "sql", "risk_check"],
        execution_trace=[
            {
                "stage": "intent",
                "status": "success",
                "metadata": {},
            },
            {
                "stage": "metadata",
                "status": "success",
                "metadata": {},
            },
            {
                "stage": "business_knowledge",
                "status": "success",
                "metadata": {},
            },
            {
                "stage": "sql_agent",
                "status": "success",
                "metadata": {},
            },
            {
                "stage": "risk_check",
                "status": "success",
                "metadata": {},
            },
            {
                "stage": "human_approval",
                "status": "pending",
                "message": "Cross join requires approval.",
                "metadata": {"reasons": ["cross_join"]},
            }
        ],
    )

    result = evaluate_agent_behavior(case, observation)

    assert result.passed is True
    assert result.checks["human_approval"] is True
    assert result.checks["risk_type"] is True


def test_summary_reports_dimension_accuracy():
    dataset = load_evaluation_dataset()
    cases = [
        next(c for c in dataset.cases if c.case_id == "tool-001"),
        next(c for c in dataset.cases if c.case_id == "clarification-001"),
    ]

    observations = {
        "tool-001": AgentBehaviorObservation(
            outcome="execute_query",
            intent="data_query",
            tools_used=["get_schema", "get_metadata"],
        ),
        "clarification-001": AgentBehaviorObservation(
            outcome="clarification",
            intent="data_query",
            clarification_required=True,
        ),
    }

    summary = evaluate_agent_behaviors(cases, observations)

    assert summary.evaluated_cases == 2
    assert summary.passed_cases == 2
    assert summary.accuracy == 1.0
    assert summary.tool_selection_accuracy == 1.0
    assert summary.clarification_accuracy == 1.0
