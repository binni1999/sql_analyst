import pytest

from agents.sql_executor import SQLExecutor
from security.executor import SecureSQLExecutor
from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy
from tools.sql_tool import build_sql_tools

from security.query_cost import QueryPlanMetrics


class RecordingDatabase:
    def __init__(self):
        self.secure_calls = []
        self.raw_calls = []

    def execute_query(self, sql):
        self.raw_calls.append(sql)
        raise AssertionError("raw database execution must not be used")

    def execute_query_secure(self, sql, *, timeout_ms, max_result_rows):
        self.secure_calls.append((sql, timeout_ms, max_result_rows))
        return {"columns": ["value"], "rows": [[1]]}

class FakeCostGuard:
    def __init__(self, *, total_cost, max_plan_rows):
        self.total_cost = total_cost
        self.max_plan_rows = max_plan_rows
        self.calls = []

    def inspect(self, sql):
        self.calls.append(sql)



        return QueryPlanMetrics(
            total_cost=self.total_cost,
            max_plan_rows=self.max_plan_rows,
            max_node_cost=self.total_cost,
            sequential_scan_count=1,
            node_count=2,
        )

def _secure_executor(db):
    return SecureSQLExecutor(
        db,
        SQLSecurityGuardrail(
            SQLSecurityPolicy(allowed_tables=frozenset({"products"}))
        ),
    )


def test_sql_executor_never_falls_back_to_raw_database_execution():
    db = RecordingDatabase()
    executor = SQLExecutor(db)

    result = executor.execute("SELECT product_id FROM products LIMIT 10")

    assert result["success"] is True
    assert db.raw_calls == []
    assert len(db.secure_calls) == 1


def test_sql_executor_revalidates_sql_at_execution_boundary():
    db = RecordingDatabase()
    executor = SQLExecutor(db, secure_executor=_secure_executor(db))

    result = executor.execute("SELECT customer_id FROM customers LIMIT 10")

    assert result["success"] is False
    assert "security policy rejected query" in result["error"]
    assert db.secure_calls == []
    assert db.raw_calls == []


def test_sql_tool_requires_secure_executor():
    with pytest.raises(ValueError, match="secure_executor is required"):
        build_sql_tools(
            db=RecordingDatabase(),
            metadata_service=object(),
            sql_validator=object(),
            sql_generator=object(),
        )


def test_sql_tool_execution_uses_secure_executor():
    db = RecordingDatabase()
    secure = _secure_executor(db)
    tools = build_sql_tools(
        db=db,
        metadata_service=object(),
        sql_validator=object(),
        sql_generator=object(),
        secure_executor=secure,
    )

    execute_sql = next(tool for tool in tools if tool.name == "execute_sql")
    result = execute_sql.invoke({"sql": "SELECT product_id FROM products LIMIT 10"})

    assert result["success"] is True
    assert len(db.secure_calls) == 1
    assert db.raw_calls == []


def test_repaired_sql_cannot_bypass_execution_guardrail():
    db = RecordingDatabase()
    secure = _secure_executor(db)

    # Simulate a repaired query that is syntactically valid but references an
    # unauthorized table. The execution boundary must validate the final SQL,
    # regardless of how it was produced.
    with pytest.raises(PermissionError, match="security policy rejected"):
        secure.execute("SELECT customer_id FROM customers LIMIT 10")

    assert db.secure_calls == []
    assert db.raw_calls == []

def _production_guardrail():
    return SQLSecurityGuardrail(
        SQLSecurityPolicy(
            allowed_tables=frozenset(
                {
                    "customers",
                    "products",
                    "orders",
                    "order_items",
                    "payments",
                    "reviews",
                }
            )
        )
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customers LIMIT 10",
        "SELECT * FROM products LIMIT 10",
        "SELECT * FROM orders LIMIT 10",
        "SELECT * FROM order_items LIMIT 10",
        "SELECT * FROM payments LIMIT 10",
        "SELECT * FROM reviews LIMIT 10",
    ],
)
def test_production_policy_allows_business_tables(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is True


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM checkpoints LIMIT 10",
        "SELECT * FROM checkpoint_writes LIMIT 10",
        "SELECT * FROM checkpoint_migrations LIMIT 10",
        "SELECT * FROM benchmark_orders LIMIT 10",
        "SELECT * FROM benchmark_order_items LIMIT 10",
        "SELECT * FROM benchmark_order_revenue LIMIT 10",
    ],
)
def test_production_policy_blocks_internal_tables(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "table_authorization"
        for violation in result.violations
    )

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pg_catalog.pg_tables LIMIT 10",
        "SELECT * FROM information_schema.tables LIMIT 10",
    ],
)
def test_production_policy_blocks_system_tables(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "table_authorization"
        for violation in result.violations
    )

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM products; DROP TABLE products;",
        "SELECT * FROM products; DELETE FROM products;",
        "SELECT * FROM products; UPDATE products SET price = 0;",
    ],
)
def test_production_policy_blocks_multiple_statement_injection(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "single_statement"
        for violation in result.violations
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM attacker.customers LIMIT 10",
        "SELECT * FROM evil.products LIMIT 10",
        "SELECT * FROM internal.orders LIMIT 10",
    ],
)
def test_production_policy_blocks_unauthorized_schema_injection(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "schema_authorization"
        for violation in result.violations
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(20)",
        "SELECT PG_SLEEP(20)",
        "SELECT pg_catalog.pg_sleep(20)",
    ],
)
def test_production_policy_blocks_dangerous_functions(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "dangerous_function"
        for violation in result.violations
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pg_catalog.pg_tables LIMIT 10",
        "SELECT * FROM information_schema.tables LIMIT 10",
        "SELECT * FROM attacker.customers LIMIT 10",
    ],
)
def test_production_policy_blocks_schema_bypass_attempts(sql):
    result = _production_guardrail().validate(sql)

    assert result.allowed is False
    assert any(
        violation.rule == "schema_authorization"
        for violation in result.violations
    )


def test_execution_boundary_blocks_dangerous_function():
    db = RecordingDatabase()
    secure = _secure_executor(db)

    with pytest.raises(PermissionError, match="security policy rejected"):
        secure.execute("SELECT pg_sleep(20)")

    assert db.secure_calls == []
    assert db.raw_calls == []


def test_execution_boundary_blocks_schema_bypass():
    db = RecordingDatabase()
    secure = _secure_executor(db)

    with pytest.raises(PermissionError, match="security policy rejected"):
        secure.execute(
            "SELECT * FROM attacker.products LIMIT 10"
        )

    assert db.secure_calls == []
    assert db.raw_calls == []


def test_execution_boundary_blocks_multiple_statements():
    db = RecordingDatabase()
    secure = _secure_executor(db)

    with pytest.raises(PermissionError, match="security policy rejected"):
        secure.execute(
            "SELECT * FROM products LIMIT 10; "
            "DROP TABLE products;"
        )

    assert db.secure_calls == []
    assert db.raw_calls == []


def test_execution_boundary_rejects_expensive_query():
    policy = SQLSecurityPolicy(
        allowed_tables=frozenset({"products"}),
        max_query_cost=100_000,
        max_plan_rows=1_000_000,
    )

    guardrail = SQLSecurityGuardrail(policy)

    cost_guard = FakeCostGuard(
        total_cost=150_000,
        max_plan_rows=500_000,
    )

    db = RecordingDatabase()

    executor = SecureSQLExecutor(
        db,
        guardrail,
        cost_guard=cost_guard,
    )

    with pytest.raises(PermissionError, match="estimated PostgreSQL cost"):
        executor.execute(
            "SELECT product_name FROM products LIMIT 5"
        )

    assert len(cost_guard.calls) == 1
    assert db.secure_calls == []
    assert db.raw_calls == []


def test_execution_boundary_rejects_large_estimated_plan():
    policy = SQLSecurityPolicy(
        allowed_tables=frozenset({"products"}),
        max_query_cost=100_000,
        max_plan_rows=1_000_000,
    )

    guardrail = SQLSecurityGuardrail(policy)

    cost_guard = FakeCostGuard(
        total_cost=500,
        max_plan_rows=2_000_000,
    )

    db = RecordingDatabase()

    executor = SecureSQLExecutor(
        db,
        guardrail,
        cost_guard=cost_guard,
    )

    with pytest.raises(PermissionError, match="estimated plan rows"):
        executor.execute(
            "SELECT product_name FROM products LIMIT 5"
        )

    assert len(cost_guard.calls) == 1
    assert db.secure_calls == []
    assert db.raw_calls == []
