import pytest

from security.executor import SecureSQLExecutor
from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def execute_query_secure(self, sql, *, timeout_ms, max_result_rows):
        self.calls.append((sql, timeout_ms, max_result_rows))
        return {"columns": ["value"], "rows": [[1]]}


def test_secure_executor_rejects_before_database_execution():
    db = FakeDatabase()
    executor = SecureSQLExecutor(
        db,
        SQLSecurityGuardrail(SQLSecurityPolicy(allowed_tables=frozenset({"products"}))),
    )

    with pytest.raises(PermissionError, match="security policy rejected"):
        executor.execute("SELECT * FROM customers LIMIT 10")

    assert db.calls == []


def test_secure_executor_passes_timeout_and_row_limit_to_database():
    db = FakeDatabase()
    policy = SQLSecurityPolicy(query_timeout_ms=2500, max_result_rows=50)
    executor = SecureSQLExecutor(db, SQLSecurityGuardrail(policy))

    result = executor.execute("SELECT product_id FROM products LIMIT 50")

    assert result["rows"] == [[1]]
    assert db.calls == [("SELECT product_id FROM products LIMIT 50", 2500, 50)]
