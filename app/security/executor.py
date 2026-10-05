from __future__ import annotations

from typing import Any

from sqlalchemy import text

from database.service import DatabaseService

from .guardrails import SQLSecurityGuardrail


class SecureSQLExecutor:
    """Execute SQL only after the security guardrail has approved it.

    The executor is the application-side execution boundary. It applies the
    guardrail before touching the database, sets a PostgreSQL statement
    timeout, and enforces the configured result-size contract.
    """

    def __init__(
        self,
        db: DatabaseService,
        guardrail: SQLSecurityGuardrail,
    ) -> None:
        self.db = db
        self.guardrail = guardrail

    def execute(self, sql: str) -> dict[str, Any]:
        validation = self.guardrail.validate(sql)
        if not validation.allowed:
            messages = "; ".join(v.message for v in validation.violations)
            raise PermissionError(f"SQL security policy rejected query: {messages}")

        normalized_sql = validation.normalized_sql or sql.strip()
        timeout_ms = self.guardrail.policy.query_timeout_ms
        max_rows = self.guardrail.policy.max_result_rows

        # DatabaseService owns the actual SQLAlchemy connection. The secure
        # method keeps timeout handling at the real DB execution boundary.
        return self.db.execute_query_secure(
            normalized_sql,
            timeout_ms=timeout_ms,
            max_result_rows=max_rows,
        )
