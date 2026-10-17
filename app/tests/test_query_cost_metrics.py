import pytest

from observability.metrics import metrics_registry
from security.executor import SecureSQLExecutor
from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy
from security.query_cost import QueryPlanMetrics


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def execute_query_secure(
        self,
        sql,
        *,
        timeout_ms,
        max_result_rows,
    ):
        self.calls.append(
            {
                "sql": sql,
                "timeout_ms": timeout_ms,
                "max_result_rows": max_result_rows,
            }
        )

        return {
            "columns": ["value"],
            "rows": [[1]],
        }


class FakeCostGuard:
    def __init__(self, *, total_cost, max_plan_rows):
        self.total_cost = total_cost
        self.max_plan_rows = max_plan_rows

    def inspect(self, sql):
        return QueryPlanMetrics(
            total_cost=self.total_cost,
            max_plan_rows=self.max_plan_rows,
            max_node_cost=self.total_cost,
            sequential_scan_count=1,
            node_count=2,
        )


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics_registry.reset()
    yield
    metrics_registry.reset()


def build_executor(
    *,
    total_cost,
    max_plan_rows,
):
    policy = SQLSecurityPolicy(
        allowed_tables=frozenset({"products"}),
        max_query_cost=100_000.0,
        max_plan_rows=1_000_000,
    )

    guardrail = SQLSecurityGuardrail(policy)

    database = FakeDatabase()

    cost_guard = FakeCostGuard(
        total_cost=total_cost,
        max_plan_rows=max_plan_rows,
    )

    executor = SecureSQLExecutor(
        database,
        guardrail,
        cost_guard,
    )

    return executor, database


def test_cost_rejection_records_metric():
    executor, database = build_executor(
        total_cost=200_000.0,
        max_plan_rows=100,
    )

    with pytest.raises(PermissionError, match="estimated PostgreSQL cost"):
        executor.execute(
            "SELECT product_id FROM products"
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.cost_rejections"] == 1
    assert snapshot["counters"].get("sql.plan_rows_rejections", 0) == 0

    # Query must not reach the database.
    assert database.calls == []


def test_plan_rows_rejection_records_metric():
    executor, database = build_executor(
        total_cost=100.0,
        max_plan_rows=2_000_000,
    )

    with pytest.raises(PermissionError, match="estimated plan rows"):
        executor.execute(
            "SELECT product_id FROM products"
        )

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["sql.plan_rows_rejections"] == 1
    assert snapshot["counters"].get("sql.cost_rejections", 0) == 0

    # Query must not reach the database.
    assert database.calls == []


def test_allowed_query_does_not_record_cost_rejection():
    executor, database = build_executor(
        total_cost=100.0,
        max_plan_rows=100,
    )

    result = executor.execute(
        "SELECT product_id FROM products"
    )

    assert result["rows"] == [[1]]

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"].get("sql.cost_rejections", 0) == 0
    assert snapshot["counters"].get("sql.plan_rows_rejections", 0) == 0

    assert len(database.calls) == 1

def test_cost_inspection_failure_prevents_database_execution():
    class FailingCostGuard:
        def inspect(self, sql):
            raise RuntimeError("EXPLAIN failed")

    policy = SQLSecurityPolicy(
        allowed_tables=frozenset({"products"}),
        max_query_cost=100_000.0,
        max_plan_rows=1_000_000,
    )
    guardrail = SQLSecurityGuardrail(policy)
    database = FakeDatabase()

    executor = SecureSQLExecutor(
        database,
        guardrail,
        FailingCostGuard(),
    )

    with pytest.raises(RuntimeError, match="EXPLAIN failed"):
        executor.execute("SELECT product_id FROM products")

    assert database.calls == []