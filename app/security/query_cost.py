from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from database.dbconnect import readonly_engine


@dataclass(frozen=True)
class QueryPlanMetrics:
    """Estimated metrics extracted from a PostgreSQL EXPLAIN plan."""

    total_cost: float
    max_plan_rows: int
    max_node_cost: float
    sequential_scan_count: int
    node_count: int


class QueryCostGuard:
    """Inspect PostgreSQL's estimated execution plan.

    This guard uses EXPLAIN without ANALYZE, so the query is not executed.
    The SQL passed here must already have passed the SQL security guardrail.
    """

    def __init__(self, engine=readonly_engine) -> None:
        self.engine = engine

    def inspect(self, sql: str) -> QueryPlanMetrics:
        """Return estimated execution-plan metrics for a validated SQL query."""

        with self.engine.connect() as connection:
            result = connection.execute(
                text("EXPLAIN (FORMAT JSON) " + sql)
            )
            payload = result.scalar_one()

        plan = payload[0]["Plan"]

        metrics: dict[str, Any] = {
            "total_cost": float(plan.get("Total Cost", 0.0)),
            "max_plan_rows": 0,
            "max_node_cost": 0.0,
            "sequential_scan_count": 0,
            "node_count": 0,
        }

        self._walk_plan(plan, metrics)

        return QueryPlanMetrics(**metrics)

    def _walk_plan(
        self,
        node: dict[str, Any],
        metrics: dict[str, Any],
    ) -> None:
        metrics["node_count"] += 1

        plan_rows = int(node.get("Plan Rows", 0))
        total_cost = float(node.get("Total Cost", 0.0))

        metrics["max_plan_rows"] = max(
            metrics["max_plan_rows"],
            plan_rows,
        )

        metrics["max_node_cost"] = max(
            metrics["max_node_cost"],
            total_cost,
        )

        if node.get("Node Type") == "Seq Scan":
            metrics["sequential_scan_count"] += 1

        for child in node.get("Plans", []):
            self._walk_plan(child, metrics)