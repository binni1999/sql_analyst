from pathlib import Path

from evaluation.dashboard import render_evaluation_dashboard, save_evaluation_dashboard
from evaluation.harness import EvaluationCaseResult, EvaluationRuntime, EvaluationSummary


def _summary() -> EvaluationSummary:
    runtime = EvaluationRuntime(
        case_id="revenue",
        conversation_id="eval-1",
        final_question="Show revenue",
        generated_sql="SELECT SUM(quantity) FROM order_items",
        generated_answer="Total revenue is 100.",
        success=True,
        total_duration_ms=123.4,
        execution_trace=[
            {"stage": "sql_agent", "status": "success", "message": "generated"}
        ],
    )
    return EvaluationSummary(
        dataset_id="sql_analyst_core",
        dataset_version="1.0.0",
        evaluated_cases=1,
        passed_cases=1,
        accuracy=1.0,
        sql_evaluated_cases=1,
        sql_matched_cases=1,
        sql_accuracy=1.0,
        total_duration_ms=123.4,
        results=[EvaluationCaseResult(case_id="revenue", runtime=runtime)],
    )


def test_dashboard_contains_summary_and_case_data():
    html = render_evaluation_dashboard(_summary())

    assert "Multi-Agent SQL Analyst" in html
    assert "sql_analyst_core" in html
    assert "100.0%" in html
    assert "revenue" in html
    assert "execution trace" in html
    assert "window.__evaluationData" in html


def test_dashboard_escapes_case_ids():
    summary = _summary()
    summary.results[0].case_id = "<script>alert(1)</script>"

    html = render_evaluation_dashboard(summary)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_save_dashboard_writes_html(tmp_path: Path):
    output = save_evaluation_dashboard(_summary(), tmp_path / "report" / "evaluation.html")

    assert output.exists()
    assert output.suffix == ".html"
    assert "sql_analyst_core" in output.read_text(encoding="utf-8")
