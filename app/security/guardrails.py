from __future__ import annotations

import sqlglot
from sqlglot import exp

from .models import GuardrailResult, GuardrailViolation
from .policies import SQLSecurityPolicy


class SQLSecurityGuardrail:
    """Hard security boundary before SQL is allowed to execute.

    The guardrail owns authorization and execution-safety policy. It does not
    replace the existing SQL/schema validator used by the SQL agent.
    """

    def __init__(self, policy: SQLSecurityPolicy | None = None):
        self.policy = policy or SQLSecurityPolicy()

    def validate(self, sql: str) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        normalized_sql: str | None = None

        if not isinstance(sql, str) or not sql.strip():
            violations.append(
                GuardrailViolation(
                    rule="empty_sql",
                    message="SQL query must not be empty.",
                )
            )
            return GuardrailResult(allowed=False, violations=violations)

        if len(sql) > self.policy.max_query_length:
            violations.append(
                GuardrailViolation(
                    rule="query_length",
                    message=(
                        "SQL query exceeds the configured maximum length "
                        f"of {self.policy.max_query_length} characters."
                    ),
                )
            )
            return GuardrailResult(allowed=False, violations=violations)

        try:
            statements = sqlglot.parse(sql, dialect="postgres")
        except Exception as exc:
            violations.append(
                GuardrailViolation(
                    rule="sql_parse",
                    message=f"SQL could not be parsed: {exc}",
                )
            )
            return GuardrailResult(allowed=False, violations=violations)

        if len(statements) != 1:
            violations.append(
                GuardrailViolation(
                    rule="single_statement",
                    message="Only one SQL statement is allowed per request.",
                )
            )
            return GuardrailResult(allowed=False, violations=violations)

        expression = statements[0]

        if not isinstance(expression, exp.Select):
            violations.append(
                GuardrailViolation(
                    rule="select_only",
                    message="Only SELECT queries are permitted.",
                )
            )

        if isinstance(expression, exp.Select):
            violations.extend(self._validate_query_features(expression))
            violations.extend(self._validate_table_authorization(expression))
            violations.extend(self._validate_column_authorization(expression))

        if violations:
            return GuardrailResult(allowed=False, violations=violations)

        try:
            normalized_sql = expression.sql(dialect="postgres")
        except Exception:
            normalized_sql = sql.strip()

        return GuardrailResult(
            allowed=True,
            normalized_sql=normalized_sql,
        )

    def _validate_query_features(self, expression: exp.Select):
        violations: list[GuardrailViolation] = []

        if not self.policy.allow_cte and expression.args.get("with") is not None:
            violations.append(
                GuardrailViolation(
                    rule="cte_policy",
                    message="CTEs are not permitted by the security policy.",
                )
            )

        subqueries = list(expression.find_all(exp.Subquery))
        if not self.policy.allow_subqueries and subqueries:
            violations.append(
                GuardrailViolation(
                    rule="subquery_policy",
                    message="Subqueries are not permitted by the security policy.",
                )
            )

        joins = list(expression.find_all(exp.Join))
        if len(joins) > self.policy.max_joins:
            violations.append(
                GuardrailViolation(
                    rule="max_joins",
                    message=(
                        f"Query contains {len(joins)} joins, exceeding the "
                        f"configured maximum of {self.policy.max_joins}."
                    ),
                )
            )

        if len(subqueries) > self.policy.max_subqueries:
            violations.append(
                GuardrailViolation(
                    rule="max_subqueries",
                    message=(
                        f"Query contains {len(subqueries)} subqueries, exceeding "
                        f"the configured maximum of {self.policy.max_subqueries}."
                    ),
                )
            )

        limit = expression.args.get("limit")
        limit_value = self._limit_value(limit)

        if self.policy.require_limit_for_wildcard and self._has_top_level_wildcard(expression):
            if limit is None:
                violations.append(
                    GuardrailViolation(
                        rule="wildcard_requires_limit",
                        message=(
                            "Wildcard result queries must include a LIMIT to "
                            "prevent unbounded result sets."
                        ),
                    )
                )

        if limit_value is not None and limit_value > self.policy.max_result_rows:
            violations.append(
                GuardrailViolation(
                    rule="max_result_rows",
                    message=(
                        f"Query LIMIT {limit_value} exceeds the configured "
                        f"maximum result size of {self.policy.max_result_rows} rows."
                    ),
                )
            )

        if (
            self.policy.require_limit_for_large_result
            and self._is_potentially_large_result(expression)
            and limit is None
        ):
            violations.append(
                GuardrailViolation(
                    rule="large_result_requires_limit",
                    message=(
                        "Row-producing queries must include a LIMIT to prevent "
                        "unbounded result sets."
                    ),
                )
            )

        return violations

    @staticmethod
    def _limit_value(limit: exp.Expression | None) -> int | None:
        if limit is None:
            return None
        expression = getattr(limit, "expression", None)
        if isinstance(expression, exp.Literal) and expression.is_int:
            return int(expression.this)
        return None

    @staticmethod
    def _is_potentially_large_result(expression: exp.Select) -> bool:
        """Return whether a SELECT can produce an unbounded row set.

        Aggregate-only queries such as ``COUNT(*)`` are scalar-style results and
        do not need a LIMIT. Queries reading rows from a table without a LIMIT
        are conservatively treated as potentially large.
        """
        if expression.args.get("from") is None:
            return False

        # GROUP BY can still return one row per group, even when aggregate
        # functions are present, so it remains a potentially large result.
        if expression.args.get("group") is not None:
            return True

        aggregate_types = (
            exp.Avg,
            exp.Count,
            exp.Max,
            exp.Min,
            exp.Sum,
        )
        return not any(expression.find_all(*aggregate_types))

    @staticmethod
    def _has_top_level_wildcard(expression: exp.Select) -> bool:
        """Return whether the SELECT projection directly returns a wildcard.

        ``COUNT(*)`` is intentionally not treated as a wildcard result because
        it returns an aggregate scalar rather than all underlying rows.
        Qualified wildcards such as ``orders.*`` are handled as well.
        """
        for projection in expression.expressions:
            if isinstance(projection, exp.Star):
                return True
            if isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                return True
        return False

    def _cte_names(self, expression: exp.Select) -> set[str]:
        return {
            cte.alias.lower()
            for cte in expression.find_all(exp.CTE)
            if cte.alias
        }

    def _physical_tables(self, expression: exp.Select) -> list[exp.Table]:
        cte_names = self._cte_names(expression)
        return [
            table
            for table in expression.find_all(exp.Table)
            if table.name and table.name.lower() not in cte_names
        ]

    def _validate_table_authorization(self, expression: exp.Select):
        allowed = self.policy.normalized_allowed_tables()
        if allowed is None:
            return []

        violations: list[GuardrailViolation] = []
        seen: set[str] = set()

        for table in self._physical_tables(expression):
            table_name = table.name
            normalized_name = table_name.lower()
            if normalized_name in seen:
                continue
            seen.add(normalized_name)

            if normalized_name not in allowed:
                violations.append(
                    GuardrailViolation(
                        rule="table_authorization",
                        message=(
                            f"Table '{table_name}' is not authorized "
                            "for this SQL agent."
                        ),
                    )
                )

        return violations

    def _validate_column_authorization(self, expression: exp.Select):
        """Enforce allowed/sensitive columns without rewriting the SQL.

        Authorization is deny-by-default for a table whenever that table has
        an explicit ``allowed_columns`` policy. Sensitive columns are always
        denied, even if they accidentally appear in an allowlist.

        For ``SELECT *`` we cannot prove which columns will be returned, so a
        star is rejected whenever a referenced table has an explicit column
        policy or sensitive-column policy. This avoids silently leaking a
        protected column through wildcard expansion.
        """
        allowed_columns = self.policy.normalized_allowed_columns()
        sensitive_columns = self.policy.normalized_sensitive_columns()

        if not allowed_columns and not sensitive_columns:
            return []

        tables = self._physical_tables(expression)
        aliases = self._table_aliases(tables)
        violations: list[GuardrailViolation] = []

        for star in expression.find_all(exp.Star):
            # A qualified star such as orders.* has a table qualifier.
            qualifier = getattr(star, "table", None)
            if qualifier:
                resolved = aliases.get(qualifier.lower(), qualifier.lower())
                if self._table_has_column_policy(
                    resolved, allowed_columns, sensitive_columns
                ):
                    violations.append(
                        GuardrailViolation(
                            rule="column_authorization",
                            message=(
                                f"Wildcard selection '{qualifier}.*' is not "
                                f"permitted for protected table '{resolved}'. "
                                "Select explicitly authorized columns."
                            ),
                        )
                    )
                continue

            protected_tables = [
                table.name.lower()
                for table in tables
                if self._table_has_column_policy(
                    table.name.lower(), allowed_columns, sensitive_columns
                )
            ]
            if protected_tables:
                violations.append(
                    GuardrailViolation(
                        rule="column_authorization",
                        message=(
                            "Wildcard selection '*' is not permitted when "
                            "column authorization applies to: "
                            + ", ".join(sorted(set(protected_tables)))
                            + ". Select explicitly authorized columns."
                        ),
                    )
                )

        for column in expression.find_all(exp.Column):
            column_name = column.name
            if not column_name:
                continue

            qualifier = column.table
            if qualifier:
                resolved_tables = self._resolve_qualifier(qualifier, aliases)
            else:
                resolved_tables = self._resolve_unqualified_column(
                    column_name, tables, allowed_columns, sensitive_columns
                )

            for table_name in resolved_tables:
                violations.extend(
                    self._check_column(
                        table_name,
                        column_name,
                        allowed_columns,
                        sensitive_columns,
                    )
                )

        return self._deduplicate_violations(violations)

    @staticmethod
    def _table_aliases(tables: list[exp.Table]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for table in tables:
            name = table.name.lower()
            aliases[name] = name
            alias = table.alias
            if alias:
                aliases[alias.lower()] = name
        return aliases

    @staticmethod
    def _resolve_qualifier(qualifier: str, aliases: dict[str, str]) -> list[str]:
        resolved = aliases.get(qualifier.lower())
        return [resolved] if resolved else [qualifier.lower()]

    @staticmethod
    def _resolve_unqualified_column(
        column_name: str,
        tables: list[exp.Table],
        allowed_columns: dict[str, frozenset[str]],
        sensitive_columns: dict[str, frozenset[str]],
    ) -> list[str]:
        """Resolve an unqualified column conservatively.

        If only one table is present, it is unambiguous. With multiple tables,
        check every table that has a column policy. This intentionally favors
        safety over trying to infer database schema that the guardrail does
        not own.
        """
        if len(tables) == 1:
            return [tables[0].name.lower()]

        protected = [
            table.name.lower()
            for table in tables
            if table.name.lower() in allowed_columns
            or table.name.lower() in sensitive_columns
        ]
        return protected

    @staticmethod
    def _table_has_column_policy(
        table_name: str,
        allowed_columns: dict[str, frozenset[str]],
        sensitive_columns: dict[str, frozenset[str]],
    ) -> bool:
        return table_name.lower() in allowed_columns or table_name.lower() in sensitive_columns

    @staticmethod
    def _check_column(
        table_name: str,
        column_name: str,
        allowed_columns: dict[str, frozenset[str]],
        sensitive_columns: dict[str, frozenset[str]],
    ) -> list[GuardrailViolation]:
        table = table_name.lower()
        column = column_name.lower()
        violations: list[GuardrailViolation] = []

        if column in sensitive_columns.get(table, frozenset()):
            violations.append(
                GuardrailViolation(
                    rule="sensitive_column",
                    message=(
                        f"Column '{table_name}.{column_name}' is sensitive "
                        "and cannot be selected."
                    ),
                )
            )

        if table in allowed_columns and column not in allowed_columns[table]:
            violations.append(
                GuardrailViolation(
                    rule="column_authorization",
                    message=(
                        f"Column '{table_name}.{column_name}' is not "
                        "authorized for this SQL agent."
                    ),
                )
            )

        return violations

    @staticmethod
    def _deduplicate_violations(
        violations: list[GuardrailViolation],
    ) -> list[GuardrailViolation]:
        seen: set[tuple[str, str]] = set()
        result: list[GuardrailViolation] = []
        for violation in violations:
            key = (violation.rule, violation.message)
            if key not in seen:
                seen.add(key)
                result.append(violation)
        return result
