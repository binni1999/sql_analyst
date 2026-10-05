from __future__ import annotations

from sqlglot import exp, parse_one

from models.human_approval import RiskAssessment


class SQLRiskChecker:
    """Deterministically classify potentially expensive/unusual SQL.

    This is intentionally conservative and read-only. It does not execute SQL
    and it does not grant permission to bypass the existing SQL validators.
    """

    def assess(self, sql: str) -> RiskAssessment:
        checks: list[str] = []
        reasons: list[str] = []

        try:
            tree = parse_one(sql, read="postgres")
        except Exception as exc:
            return RiskAssessment(
                is_risky=True,
                risk_level="high",
                reasons=[f"SQL could not be parsed for risk assessment: {exc}"],
                checks=["sql_parse"],
            )

        if not isinstance(tree, exp.Select):
            return RiskAssessment(
                is_risky=True,
                risk_level="high",
                reasons=["Only SELECT statements are eligible for this read-only workflow."],
                checks=["statement_type"],
            )

        joins = list(tree.find_all(exp.Join))
        sql_upper = sql.upper()
        has_cross_join = "CROSS JOIN" in sql_upper or any(
            (join.args.get("kind") or "").upper() == "CROSS"
            for join in joins
        )
        has_limit = tree.args.get("limit") is not None
        has_order = tree.args.get("order") is not None
        has_group = tree.args.get("group") is not None
        has_aggregation = bool(list(tree.find_all(exp.AggFunc)))
        has_star = bool(list(tree.find_all(exp.Star)))
        has_where = tree.args.get("where") is not None
        subquery_count = sum(1 for _ in tree.find_all(exp.Subquery))

        checks.extend(
            [
                "statement_type",
                "join_complexity",
                "limit_presence",
                "wildcard_scan",
                "aggregation_scan",
                "subquery_complexity",
            ]
        )

        if has_cross_join:
            reasons.append("CROSS JOIN can create a large intermediate result set.")

        if len(joins) >= 3:
            reasons.append("Query contains three or more joins and may be expensive to execute.")

        if joins and not has_limit:
            reasons.append("Joined query has no LIMIT and may scan or return a large result set.")

        if has_star and not has_limit:
            reasons.append("Wildcard projection without LIMIT may return a large result set.")

        if has_aggregation and not has_where and not has_limit:
            reasons.append("Unfiltered aggregation may require scanning a large table.")

        if has_order and not has_limit:
            reasons.append("ORDER BY without LIMIT may require sorting a large result set.")

        if subquery_count >= 2:
            reasons.append("Query contains multiple subqueries and may have higher execution cost.")

        if not reasons:
            return RiskAssessment(
                is_risky=False,
                risk_level="low",
                reasons=[],
                checks=checks,
            )

        level = "high" if has_cross_join or len(joins) >= 3 or subquery_count >= 2 else "medium"
        return RiskAssessment(
            is_risky=True,
            risk_level=level,
            reasons=reasons,
            checks=checks,
        )
