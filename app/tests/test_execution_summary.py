from services.execution_summary import ExecutionSummaryService


def test_execution_summary_counts_validation_failure_and_repair():
    execution_trace = [
        {
            "stage": "sql_agent",
            "status": "started",
            "attempt": 1,
            "duration_ms": 100.0,
        },
        {
            "stage": "sqlglot_validation",
            "status": "failed",
            "attempt": 1,
            "duration_ms": 20.0,
        },
        {
            "stage": "repair",
            "status": "success",
            "attempt": 1,
            "duration_ms": 50.0,
        },
        {
            "stage": "sqlglot_validation",
            "status": "success",
            "attempt": 2,
            "duration_ms": 30.0,
        },
    ]

    summary = ExecutionSummaryService.build(
        execution_trace=execution_trace,
        successful=True,
    )

    assert summary.total_events == 4
    assert summary.total_duration_ms == 200.0
    assert summary.retry_count == 1
    assert summary.validation_failures == 1
    assert summary.repairs == 1
    assert summary.successful is True


def test_execution_summary_with_empty_trace():
    summary = ExecutionSummaryService.build(
        execution_trace=[],
        successful=False,
    )

    assert summary.total_events == 0
    assert summary.total_duration_ms == 0.0
    assert summary.retry_count == 0
    assert summary.validation_failures == 0
    assert summary.repairs == 0
    assert summary.successful is False


def test_execution_summary_counts_multiple_validation_failures():
    execution_trace = [
        {
            "stage": "sqlglot_validation",
            "status": "failed",
            "attempt": 1,
            "duration_ms": 10.0,
        },
        {
            "stage": "database_validation",
            "status": "failed",
            "attempt": 1,
            "duration_ms": 15.0,
        },
        {
            "stage": "semantic_validation",
            "status": "failed",
            "attempt": 1,
            "duration_ms": 20.0,
        },
        {
            "stage": "context_validation",
            "status": "failed",
            "attempt": 1,
            "duration_ms": 25.0,
        },
    ]

    summary = ExecutionSummaryService.build(
        execution_trace=execution_trace,
        successful=False,
    )

    assert summary.total_events == 4
    assert summary.total_duration_ms == 70.0
    assert summary.validation_failures == 4
    assert summary.repairs == 0
    assert summary.retry_count == 0
    assert summary.successful is False