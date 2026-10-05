import pytest

from evaluation.dataset import load_evaluation_dataset
from evaluation.sql_evaluator import SQLAccuracyEvaluator, evaluate_sql


def test_equivalent_sql_matches_after_normalization():
    expected = "SELECT SUM(quantity) AS total_quantity FROM order_items"
    generated = " select  sum(quantity)  as total_quantity\nfrom order_items "

    result = evaluate_sql(expected, generated)

    assert result.evaluated is True
    assert result.match is True
    assert result.tables_match is True
    assert result.generated_tables == ["order_items"]


def test_different_metric_expression_does_not_match():
    expected = "SELECT SUM(quantity) AS total_quantity FROM order_items"
    generated = "SELECT COUNT(quantity) AS total_quantity FROM order_items"

    result = evaluate_sql(expected, generated)

    assert result.match is False
    assert result.tables_match is True


def test_different_table_does_not_match():
    expected = "SELECT SUM(quantity) AS total_quantity FROM order_items"
    generated = "SELECT SUM(quantity) AS total_quantity FROM orders"

    result = evaluate_sql(expected, generated)

    assert result.match is False
    assert result.tables_match is False
    assert result.expected_tables == ["order_items"]
    assert result.generated_tables == ["orders"]


def test_invalid_generated_sql_is_reported_without_raising():
    result = evaluate_sql(
        "SELECT SUM(quantity) FROM order_items",
        "SELECT FROM",
    )

    assert result.match is False
    assert result.error is not None
    assert "parsing failed" in result.error.lower()


def test_cases_without_expected_sql_are_not_evaluated():
    result = evaluate_sql(None, "SELECT 1")

    assert result.evaluated is False
    assert result.match is False
    assert result.error is not None


def test_evaluate_case_uses_dataset_ground_truth():
    dataset = load_evaluation_dataset()
    case = next(case for case in dataset.cases if case.case_id == "revenue-001")

    evaluator = SQLAccuracyEvaluator()
    result = evaluator.evaluate_case(case, case.expected_sql)

    assert result.case_id == "revenue-001"
    assert result.match is True
    assert result.expected_tables == ["order_items"]


def test_summary_excludes_cases_without_expected_sql():
    evaluator = SQLAccuracyEvaluator()

    results = [
        evaluator.evaluate(
            "SELECT SUM(quantity) FROM order_items",
            "SELECT SUM(quantity) FROM order_items",
            case_id="one",
        ),
        evaluator.evaluate(None, "SELECT 1", case_id="clarification"),
        evaluator.evaluate(
            "SELECT SUM(quantity) FROM order_items",
            "SELECT COUNT(quantity) FROM order_items",
            case_id="two",
        ),
    ]

    summary = evaluator.summarize(results)

    assert summary.evaluated_cases == 2
    assert summary.matched_cases == 1
    assert summary.accuracy == pytest.approx(0.5)


def test_dataset_evaluation_can_be_aggregated_by_case_id():
    dataset = load_evaluation_dataset()
    evaluator = SQLAccuracyEvaluator()

    generated_sql = {
        case.case_id: case.expected_sql
        for case in dataset.cases
        if case.expected_sql is not None
    }

    summary = evaluator.evaluate_cases(dataset.cases, generated_sql)

    assert summary.evaluated_cases > 0
    assert summary.matched_cases == summary.evaluated_cases
    assert summary.accuracy == 1.0
