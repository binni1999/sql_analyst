from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp
from pydantic import BaseModel, Field

from database.metadata import METRIC_METADATA
from evaluation.models import EvaluationCase


class SemanticComparisonResult(BaseModel):
    """Semantic evaluation result for one generated SQL statement."""

    case_id: str | None = None
    evaluated: bool = True
    match: bool = False
    generated_sql: str | None = None

    expected_metric: str | None = None
    detected_metric: str | None = None
    metric_match: bool = False
    formula_match: bool | None = None

    expected_tables: list[str] = Field(default_factory=list)
    generated_tables: list[str] = Field(default_factory=list)
    tables_match: bool = False

    expected_context: dict[str, Any] | None = None
    context_checks: dict[str, bool] = Field(default_factory=dict)

    errors: list[str] = Field(default_factory=list)


class SemanticAccuracySummary(BaseModel):
    """Aggregate semantic-accuracy results."""

    evaluated_cases: int = 0
    matched_cases: int = 0
    accuracy: float = 0.0
    results: list[SemanticComparisonResult] = Field(default_factory=list)


class SemanticAccuracyEvaluator:
    """Evaluate whether generated SQL satisfies the analytical meaning.

    Structural SQL equality belongs to ``SQLAccuracyEvaluator``. This evaluator
    instead checks the semantic contract represented by the evaluation dataset:
    metric/formula, referenced tables, grouping entity, limit, ordering,
    filters, and time ranges.
    """

    DIALECT = "postgres"

    def evaluate_case(
        self,
        case: EvaluationCase,
        generated_sql: str | None,
    ) -> SemanticComparisonResult:
        if case.expected_sql is None and case.expected_metric is None:
            return SemanticComparisonResult(
                case_id=case.case_id,
                evaluated=False,
                generated_sql=generated_sql,
                expected_metric=case.expected_metric,
                expected_context=(
                    case.expected_analytical_context.model_dump()
                    if case.expected_analytical_context
                    else None
                ),
                errors=["No semantic ground truth is defined for this case."],
            )

        if not generated_sql or not generated_sql.strip():
            return SemanticComparisonResult(
                case_id=case.case_id,
                generated_sql=generated_sql,
                expected_metric=case.expected_metric,
                expected_tables=sorted(t.lower() for t in case.expected_tables),
                expected_context=self._context_dict(case),
                errors=["Generated SQL is empty."],
            )

        try:
            tree = sqlglot.parse_one(generated_sql, read=self.DIALECT)
        except Exception as exc:
            return SemanticComparisonResult(
                case_id=case.case_id,
                generated_sql=generated_sql,
                expected_metric=case.expected_metric,
                expected_tables=sorted(t.lower() for t in case.expected_tables),
                expected_context=self._context_dict(case),
                errors=[f"Unable to parse generated SQL: {exc}"],
            )

        generated_tables = self._extract_tables(tree)
        expected_tables = sorted(t.lower() for t in case.expected_tables)
        tables_match = (
            generated_tables == expected_tables
            if expected_tables
            else True
        )

        detected_metric = self._detect_metric(tree, case.expected_metric)
        metric_match = (
            detected_metric == case.expected_metric
            if case.expected_metric
            else True
        )

        formula_match = None
        if case.expected_metric:
            formula_match = self._formula_matches_metric(
                tree,
                case.expected_metric,
            )

        context_checks: dict[str, bool] = {}
        errors: list[str] = []

        if not tables_match:
            errors.append(
                f"Expected tables {expected_tables}, found {generated_tables}."
            )

        if case.expected_metric and not metric_match:
            errors.append(
                f"Expected metric '{case.expected_metric}', "
                f"but detected '{detected_metric}'."
            )

        if case.expected_metric and formula_match is False:
            errors.append(
                f"Generated expression does not match the semantic definition "
                f"of metric '{case.expected_metric}'."
            )

        context = case.expected_analytical_context
        if context:
            context_checks = self._validate_context(tree, context)
            for name, passed in context_checks.items():
                if not passed:
                    errors.append(f"Analytical context requirement failed: {name}.")

        # Some dataset cases intentionally encode a filter/time requirement in
        # expected_result even when no AnalyticalContext was persisted.
        if case.expected_result:
            result_checks = self._validate_result_contract(
                tree,
                case.expected_result,
            )
            context_checks.update(result_checks)
            for name, passed in result_checks.items():
                if not passed:
                    errors.append(f"Result semantic requirement failed: {name}.")

        match = (
            tables_match
            and metric_match
            and formula_match is not False
            and all(context_checks.values())
            and not errors
        )

        return SemanticComparisonResult(
            case_id=case.case_id,
            generated_sql=generated_sql,
            expected_metric=case.expected_metric,
            detected_metric=detected_metric,
            metric_match=metric_match,
            formula_match=formula_match,
            expected_tables=expected_tables,
            generated_tables=generated_tables,
            tables_match=tables_match,
            expected_context=self._context_dict(case),
            context_checks=context_checks,
            errors=errors,
            match=match,
        )

    def summarize(
        self,
        results: list[SemanticComparisonResult],
    ) -> SemanticAccuracySummary:
        evaluated = [r for r in results if r.evaluated]
        matched = [r for r in evaluated if r.match]
        return SemanticAccuracySummary(
            evaluated_cases=len(evaluated),
            matched_cases=len(matched),
            accuracy=len(matched) / len(evaluated) if evaluated else 0.0,
            results=results,
        )

    def evaluate_cases(
        self,
        cases: list[EvaluationCase],
        generated_sql_by_case: dict[str, str | None],
    ) -> SemanticAccuracySummary:
        results = [
            self.evaluate_case(case, generated_sql_by_case.get(case.case_id))
            for case in cases
        ]
        return self.summarize(results)

    @staticmethod
    def _context_dict(case: EvaluationCase) -> dict[str, Any] | None:
        if case.expected_analytical_context is None:
            return None
        return case.expected_analytical_context.model_dump(exclude_none=True)

    @staticmethod
    def _extract_tables(tree: exp.Expression) -> list[str]:
        return sorted({
            table.name.lower()
            for table in tree.find_all(exp.Table)
            if table.name
        })

    def _detect_metric(
        self,
        tree: exp.Expression,
        expected_metric: str | None,
    ) -> str | None:
        if expected_metric is None:
            return None

        expressions = self._metric_expressions(tree, expected_metric)
        if expressions:
            return expected_metric

        # Generic semantic recognition for metrics not currently present in
        # METRIC_METADATA (for example rating in the evaluation dataset).
        for aggregate in tree.find_all(exp.Avg):
            if any(
                column.name.lower() == expected_metric.lower()
                for column in aggregate.find_all(exp.Column)
            ):
                return expected_metric

        for aggregate in tree.find_all(exp.Count):
            return expected_metric if expected_metric == "reviews" else None

        return None

    def _metric_expressions(
        self,
        tree: exp.Expression,
        metric: str,
    ) -> list[exp.Expression]:
        aliases = {metric.lower(), f"total_{metric.lower()}"}
        matches: list[exp.Expression] = []

        for alias in tree.find_all(exp.Alias):
            alias_name = alias.alias
            if alias_name and alias_name.lower() in aliases:
                matches.append(alias.this)

        # Also support canonical aggregate expressions without an alias.
        metadata = METRIC_METADATA.get(metric)
        if metadata:
            expected = self._parse_formula(metadata.get("formula"))
            if expected is not None:
                for aggregate in tree.find_all(exp.AggFunc):
                    if self._expressions_equal(aggregate, expected):
                        matches.append(aggregate)

        return matches

    def _formula_matches_metric(
        self,
        tree: exp.Expression,
        metric: str,
    ) -> bool | None:
        metadata = METRIC_METADATA.get(metric)
        if not metadata or metadata.get("formula_type") != "sql_expression":
            # Dataset-specific metric semantics for rating/reviews.
            if metric == "rating":
                return any(
                    isinstance(node, exp.Avg)
                    and any(c.name.lower() == "rating" for c in node.find_all(exp.Column))
                    for node in tree.find_all(exp.Avg)
                )
            if metric == "reviews":
                return any(isinstance(node, exp.Count) for node in tree.find_all(exp.Count))
            return None

        expected = self._parse_formula(metadata.get("formula"))
        if expected is None:
            return False

        expressions = self._metric_expressions(tree, metric)
        return any(self._expressions_equal(expr, expected) for expr in expressions)

    def _validate_context(
        self,
        tree: exp.Expression,
        context,
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}

        if context.entity:
            checks["entity_grouping"] = self._entity_grouping_matches(
                tree,
                context.entity,
            )

        if context.metric:
            checks["metric"] = self._detect_metric(tree, context.metric) == context.metric

        if context.limit is not None:
            checks["limit"] = self._extract_limit(tree) == context.limit

        if context.sort_direction:
            checks["sort_direction"] = (
                self._extract_sort_direction(tree) == context.sort_direction.lower()
            )

        if context.time_range:
            checks["time_range"] = self._time_range_matches(tree, context.time_range)

        for index, filter_requirement in enumerate(context.filters):
            checks[f"filter_{index}"] = self._filter_matches(tree, filter_requirement)

        return checks

    def _validate_result_contract(
        self,
        tree: exp.Expression,
        contract: dict[str, Any],
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}

        if contract.get("limit") is not None:
            checks["result_limit"] = self._extract_limit(tree) == contract["limit"]

        ordering = contract.get("ordering")
        if ordering and ordering.endswith("_desc"):
            checks["result_order_desc"] = self._extract_sort_direction(tree) == "desc"

        time_filter = contract.get("time_filter")
        if time_filter:
            checks["result_time_filter"] = self._time_range_matches(
                tree,
                {"type": "year", "year": time_filter.get("year")},
            )

        expected_filter = contract.get("filter")
        if expected_filter:
            checks["result_filter"] = self._filter_text_present(tree, expected_filter)

        formula = contract.get("formula")
        if formula and contract.get("type") == "scalar":
            parsed = self._parse_formula(formula)
            if parsed is not None:
                checks["result_formula"] = any(
                    self._expressions_equal(node, parsed)
                    for node in tree.find_all(exp.AggFunc)
                )

        return checks

    @staticmethod
    def _parse_formula(formula: str | None) -> exp.Expression | None:
        if not formula:
            return None
        try:
            return sqlglot.parse_one(
                f"SELECT {formula}",
                read="postgres",
            ).expressions[0]
        except Exception:
            return None

    @staticmethod
    def _expressions_equal(left: exp.Expression, right: exp.Expression) -> bool:
        left = left.copy()
        right = right.copy()
        for column in left.find_all(exp.Column):
            column.set("table", None)
        for column in right.find_all(exp.Column):
            column.set("table", None)
        return left.sql(dialect="postgres", normalize=True) == right.sql(
            dialect="postgres", normalize=True
        )

    @staticmethod
    def _extract_limit(tree: exp.Expression) -> int | None:
        limit = tree.args.get("limit")
        if not limit:
            return None
        value = limit.expression
        if isinstance(value, exp.Literal) and not value.is_string:
            try:
                return int(value.this)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _extract_sort_direction(tree: exp.Expression) -> str | None:
        order = tree.args.get("order")
        if not order or not order.expressions:
            return None
        first = order.expressions[0]
        if isinstance(first, exp.Ordered) and first.args.get("desc"):
            return "desc"
        return "asc"

    @staticmethod
    def _entity_grouping_matches(tree: exp.Expression, entity: str) -> bool:
        if entity == "product":
            return any(
                column.name.lower() in {"product_id", "product_name"}
                for group in tree.find_all(exp.Group)
                for column in group.find_all(exp.Column)
            )
        if entity == "customer":
            return any(
                column.name.lower() in {"customer_id", "customer_name"}
                for group in tree.find_all(exp.Group)
                for column in group.find_all(exp.Column)
            )
        if entity == "order":
            return any(
                column.name.lower() == "order_id"
                for group in tree.find_all(exp.Group)
                for column in group.find_all(exp.Column)
            )
        return False

    @staticmethod
    def _time_range_matches(tree: exp.Expression, time_range: dict[str, Any]) -> bool:
        if time_range.get("type") != "year":
            return False
        year = str(time_range.get("year"))
        where = tree.args.get("where")
        if where is None:
            return False
        for literal in where.find_all(exp.Literal):
            if literal.is_string and year in str(literal.this):
                return True
            if not literal.is_string and str(literal.this) == year:
                return True
        return False

    @staticmethod
    def _filter_matches(tree: exp.Expression, requirement: dict[str, Any]) -> bool:
        field = requirement.get("field")
        if not field:
            return True
        where = tree.args.get("where")
        if where is None:
            return False
        return any(
            column.name.lower() == str(field).lower()
            for column in where.find_all(exp.Column)
        )

    @staticmethod
    def _filter_text_present(tree: exp.Expression, expected_filter: str) -> bool:
        """Compare a simple filter semantically, ignoring table aliases."""

        where = tree.args.get("where")
        if where is None:
            return False

        try:
            expected_tree = sqlglot.parse_one(
                f"SELECT * FROM orders WHERE {expected_filter}",
                read="postgres",
            )
            expected_where = expected_tree.args["where"].this
        except Exception:
            return False

        actual_predicates = [
            node for node in where.find_all(exp.EQ)
        ]
        expected_predicates = [
            node for node in expected_where.find_all(exp.EQ)
        ]

        if not expected_predicates:
            return False

        def normalize_predicate(node: exp.Expression) -> str:
            node = node.copy()
            for column in node.find_all(exp.Column):
                column.set("table", None)
            return node.sql(dialect="postgres", normalize=True).lower()

        expected_normalized = {
            normalize_predicate(node) for node in expected_predicates
        }
        actual_normalized = {
            normalize_predicate(node) for node in actual_predicates
        }

        return expected_normalized.issubset(actual_normalized)
