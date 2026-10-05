import pytest

from evaluation.dataset import load_evaluation_dataset
from evaluation.semantic_evaluator import SemanticAccuracyEvaluator


@pytest.fixture
def dataset():
    return load_evaluation_dataset()


@pytest.fixture
def evaluator():
    return SemanticAccuracyEvaluator()


def get_case(dataset, case_id):
    return next(case for case in dataset.cases if case.case_id == case_id)


def test_revenue_formula_is_semantically_correct(dataset, evaluator):
    case = get_case(dataset, "revenue-001")
    sql = """
        SELECT SUM(quantity * unit_price * (1 - discount)) AS total_revenue
        FROM order_items
    """

    result = evaluator.evaluate_case(case, sql)

    assert result.match is True
    assert result.metric_match is True
    assert result.formula_match is True
    assert result.tables_match is True


def test_wrong_revenue_formula_is_semantically_incorrect(dataset, evaluator):
    case = get_case(dataset, "revenue-001")
    sql = """
        SELECT SUM(quantity * unit_price + discount) AS total_revenue
        FROM order_items
    """

    result = evaluator.evaluate_case(case, sql)

    assert result.match is False
    assert result.formula_match is False


def test_top_n_context_is_checked(dataset, evaluator):
    case = get_case(dataset, "context-001")
    sql = """
        SELECT p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC
        LIMIT 5
    """

    result = evaluator.evaluate_case(case, sql)

    assert result.match is True
    assert result.context_checks["entity_grouping"] is True
    assert result.context_checks["limit"] is True
    assert result.context_checks["sort_direction"] is True


def test_missing_limit_fails_semantic_evaluation(dataset, evaluator):
    case = get_case(dataset, "context-001")
    sql = """
        SELECT p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC
    """

    result = evaluator.evaluate_case(case, sql)

    assert result.match is False
    assert result.context_checks["limit"] is False


def test_time_filter_is_semantically_checked(dataset, evaluator):
    case = get_case(dataset, "time-001")
    sql = """
        SELECT SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS total_revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE EXTRACT(YEAR FROM o.order_date) = 2025
    """

    result = evaluator.evaluate_case(case, sql)

    assert result.match is True
    assert result.context_checks["time_range"] is True


def test_expected_sql_none_case_is_not_evaluated(dataset, evaluator):
    case = get_case(dataset, "clarification-001")

    result = evaluator.evaluate_case(case, None)

    assert result.evaluated is False
    assert result.match is False


def test_summary_excludes_non_evaluable_cases(dataset, evaluator):
    cases = [
        get_case(dataset, "revenue-001"),
        get_case(dataset, "clarification-001"),
    ]

    results = [
        evaluator.evaluate_case(
            cases[0],
            "SELECT SUM(quantity * unit_price * (1 - discount)) AS total_revenue FROM order_items",
        ),
        evaluator.evaluate_case(cases[1], None),
    ]

    summary = evaluator.summarize(results)

    assert summary.evaluated_cases == 1
    assert summary.matched_cases == 1
    assert summary.accuracy == 1.0
