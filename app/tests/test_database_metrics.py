import pytest
from sqlalchemy import text

from database.service import DatabaseService
from observability.metrics import metrics_registry


@pytest.fixture(autouse=True)
def reset_metrics():
    """
    Reset the global metrics registry before every test so
    metrics from one test do not affect another test.
    """
    metrics_registry.reset()
    yield
    metrics_registry.reset()


def test_secure_query_records_execution_and_success_metrics():
    service = DatabaseService()

    result = service.execute_query_secure(
        "SELECT 1 AS value",
        timeout_ms=5000,
        max_result_rows=10,
    )

    assert result["columns"] == ["value"]
    assert result["rows"] == [[1]]

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"]["sql.successes"] == 1
    assert snapshot["counters"].get("sql.failures", 0) == 0


def test_secure_query_enforces_read_only_transaction():
    service = DatabaseService()

    result = service.execute_query_secure(
        "SELECT current_setting('transaction_read_only') AS read_only",
        timeout_ms=5000,
        max_result_rows=10,
    )

    assert result["columns"] == ["read_only"]
    assert result["rows"] == [["on"]]


def test_secure_query_records_rows_returned():
    service = DatabaseService()

    result = service.execute_query_secure(
        """
        SELECT product_id
        FROM products
        ORDER BY product_id
        LIMIT 3
        """,
        timeout_ms=5000,
        max_result_rows=10,
    )

    assert len(result["rows"]) == 3

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"]["sql.successes"] == 1
    assert snapshot["counters"]["sql.rows_returned"] == 3


def test_secure_query_records_execution_timing():
    service = DatabaseService()

    service.execute_query_secure(
        "SELECT 1 AS value",
        timeout_ms=5000,
        max_result_rows=10,
    )

    snapshot = metrics_registry.snapshot()

    timing = snapshot["timings"]["sql.execution_ms"]

    assert timing["count"] == 1
    assert timing["total_ms"] >= 0
    assert timing["avg_ms"] >= 0
    assert timing["min_ms"] >= 0
    assert timing["max_ms"] >= 0


def test_secure_query_failure_records_failure_metric():
    service = DatabaseService()

    with pytest.raises(Exception):
        service.execute_query_secure(
            "SELECT definitely_nonexistent_column FROM products",
            timeout_ms=5000,
            max_result_rows=10,
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"]["sql.failures"] == 1
    assert snapshot["counters"]["sql.database_errors"] == 1
    assert snapshot["counters"].get("sql.successes", 0) == 0


def test_secure_query_row_limit_failure_records_failure_metric():
    service = DatabaseService()

    with pytest.raises(ValueError, match="configured maximum"):
        service.execute_query_secure(
            """
            SELECT product_id
            FROM products
            ORDER BY product_id
            LIMIT 3
            """,
            timeout_ms=5000,
            max_result_rows=2,
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"]["sql.failures"] == 1
    assert snapshot["counters"].get("sql.successes", 0) == 0
    assert snapshot["counters"]["sql.result_limit_rejections"] == 1



def test_invalid_timeout_does_not_reach_database_execution():
    service = DatabaseService()

    with pytest.raises(
        ValueError,
        match="timeout_ms must be greater than zero",
    ):
        service.execute_query_secure(
            "SELECT 1",
            timeout_ms=0,
            max_result_rows=10,
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"].get("sql.successes", 0) == 0
    assert snapshot["counters"].get("sql.failures", 0) == 0

    
def test_secure_query_timeout_records_timeout_metric():
    service = DatabaseService()

    with pytest.raises(Exception):
        service.execute_query_secure(
            "SELECT pg_sleep(2)",
            timeout_ms=250,
            max_result_rows=10,
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.executions"] == 1
    assert snapshot["counters"]["sql.failures"] == 1
    assert snapshot["counters"]["sql.timeouts"] == 1
    assert snapshot["counters"].get("sql.successes", 0) == 0