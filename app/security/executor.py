from __future__ import annotations

from typing import Any

from database.service import DatabaseService
from observability.metrics import metrics_registry

import logging

logger = logging.getLogger(__name__)

from .guardrails import SQLSecurityGuardrail
from .query_cost import QueryCostGuard


class SecureSQLExecutor:
    """Execute SQL only after the security guardrail has approved it.

    The executor is the application-side execution boundary. It applies the
    guardrail before touching the database, checks estimated query cost and
    plan size, and finally delegates execution to DatabaseService.
    """

    def __init__(
        self,
        db: DatabaseService,
        guardrail: SQLSecurityGuardrail,
        cost_guard: QueryCostGuard | None = None,
    ) -> None:
        self.db = db
        self.guardrail = guardrail
        self.cost_guard = cost_guard

    def execute(self, sql: str) -> dict[str, Any]:

        # ========================================================
        # 1. SQL Security Validation
        # ========================================================

        validation = self.guardrail.validate(sql)

        if not validation.allowed:

            # Record security rejection before raising the error.
            metrics_registry.increment(
                "sql.security_rejections"
            )

            messages = "; ".join(
                v.message
                for v in validation.violations
            )

            logger.warning(
                "sql_security_rejected",
                extra={
                    "reason": "security_policy_rejected",
                    "violations": messages,
                },
            )

            raise PermissionError(
                "SQL security policy rejected query: "
                f"{messages}"
            )

        # ========================================================
        # 2. Normalize SQL
        # ========================================================

        normalized_sql = (
            validation.normalized_sql
            or sql.strip()
        )

        # ========================================================
        # 3. Query Cost Protection
        # ========================================================

        if (
            self.cost_guard is not None
            and self.guardrail.policy.enable_query_cost_check
        ):

            metrics = self.cost_guard.inspect(
                normalized_sql
            )

            # ----------------------------------------------------
            # 3a. Estimated PostgreSQL Cost
            # ----------------------------------------------------

            if (
                metrics.total_cost
                > self.guardrail.policy.max_query_cost
            ):

                metrics_registry.increment(
                    "sql.cost_rejections"
                )

                logger.warning(
                    "query_cost_rejected",
                    extra={
                        "estimated_cost": metrics.total_cost,
                        "max_query_cost": (
                            self.guardrail.policy.max_query_cost
                        ),
                        "max_plan_rows": metrics.max_plan_rows,
                        "configured_max_plan_rows": (
                            self.guardrail.policy.max_plan_rows
                        ),
                        "sequential_scan_count": (
                            metrics.sequential_scan_count
                        ),
                        "plan_node_count": metrics.node_count,
                        "reason": "estimated_cost_exceeded",
                    },
                )

                raise PermissionError(
                    "Query rejected because estimated PostgreSQL "
                    f"cost {metrics.total_cost:.2f} exceeds the "
                    "maximum allowed cost "
                    f"{self.guardrail.policy.max_query_cost:.2f}."
                )

            # ----------------------------------------------------
            # 3b. Estimated Plan Rows
            # ----------------------------------------------------

            if (
                metrics.max_plan_rows
                > self.guardrail.policy.max_plan_rows
            ):

                metrics_registry.increment(
                    "sql.plan_rows_rejections"
                )

                logger.warning(
                    "query_cost_rejected",
                    extra={
                        "estimated_cost": metrics.total_cost,
                        "max_query_cost": (
                            self.guardrail.policy.max_query_cost
                        ),
                        "max_plan_rows": metrics.max_plan_rows,
                        "configured_max_plan_rows": (
                            self.guardrail.policy.max_plan_rows
                        ),
                        "sequential_scan_count": (
                            metrics.sequential_scan_count
                        ),
                        "plan_node_count": metrics.node_count,
                        "reason": "estimated_plan_rows_exceeded",
                    },
                )

                raise PermissionError(
                    "Query rejected because estimated plan rows "
                    f"{metrics.max_plan_rows:,} exceeds the "
                    "maximum allowed plan rows "
                    f"{self.guardrail.policy.max_plan_rows:,}."
                )

        # ========================================================
        # 4. Database Execution
        # ========================================================

        max_rows = self.guardrail.policy.max_result_rows

        # DatabaseService owns the actual SQLAlchemy connection.
        # The secure method keeps timeout handling at the real
        # database execution boundary.
        return self.db.execute_query_secure(
            normalized_sql,
            timeout_ms=self.guardrail.policy.query_timeout_ms,
            max_result_rows=max_rows,
        )