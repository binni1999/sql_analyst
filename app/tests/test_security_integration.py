import pytest

from agents.sql_executor import SQLExecutor
from security.executor import SecureSQLExecutor
from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy
from tools.sql_tool import build_sql_tools


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
