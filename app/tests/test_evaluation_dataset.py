from evaluation.dataset import load_evaluation_dataset
from evaluation.models import EvaluationCase


EXPECTED_CATEGORIES = {
    "basic_aggregation",
    "revenue",
    "quantity",
    "top_n",
    "sorting",
    "filtering",
    "time_filtering",
    "analytical_context",
    "follow_up",
    "business_knowledge",
    "clarification",
    "unsupported_request",
    "sql_repair",
    "tool_discovery",
    "human_approval",
    "multi_turn",
}


def test_default_evaluation_dataset_loads():
    dataset = load_evaluation_dataset()

    assert dataset.dataset_id == "sql_analyst_core"
    assert dataset.version == "1.0.0"
    assert len(dataset.cases) == 16


def test_evaluation_case_ids_are_unique():
    dataset = load_evaluation_dataset()
    case_ids = [case.case_id for case in dataset.cases]

    assert len(case_ids) == len(set(case_ids))


def test_dataset_covers_step_65_core_scenarios():
    dataset = load_evaluation_dataset()
    categories = {case.category for case in dataset.cases}

    assert EXPECTED_CATEGORIES <= categories


def test_every_case_has_required_ground_truth_contract():
    dataset = load_evaluation_dataset()

    for case in dataset.cases:
        assert isinstance(case, EvaluationCase)
        assert case.case_id
        assert case.category
        assert case.description
        assert case.question
        assert case.expected_behavior


def test_query_cases_define_sql_and_tables():
    dataset = load_evaluation_dataset()

    query_cases = [
        case
        for case in dataset.cases
        if case.expected_behavior.get("outcome") == "execute_query"
    ]

    assert query_cases
    assert all(case.expected_sql for case in query_cases)
    assert all(case.expected_tables for case in query_cases)
    assert all(case.expected_result for case in query_cases)


def test_business_knowledge_cases_define_expected_documents():
    dataset = load_evaluation_dataset()

    cases = [
        case for case in dataset.cases if case.category == "business_knowledge"
    ]

    assert cases
    assert all(case.expected_business_knowledge_documents for case in cases)


def test_multi_turn_cases_define_conversation_history():
    dataset = load_evaluation_dataset()

    cases = [case for case in dataset.cases if case.category == "multi_turn"]

    assert cases
    assert all(len(case.conversation) >= 2 for case in cases)
    assert all(case.expected_resolved_question for case in cases)


def test_clarification_and_hitl_cases_do_not_require_sql():
    dataset = load_evaluation_dataset()

    clarification = next(
        case for case in dataset.cases if case.category == "clarification"
    )
    hitl = next(
        case for case in dataset.cases if case.category == "human_approval"
    )

    assert clarification.expected_sql is None
    assert clarification.expected_behavior["clarification"] is True
    assert hitl.expected_sql is None
    assert hitl.expected_behavior["human_approval"] is True
