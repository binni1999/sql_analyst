from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp
from pydantic import BaseModel, Field

from evaluation.models import EvaluationCase


class SQLComparisonResult(BaseModel):
    """Deterministic comparison result for one expected/generated SQL pair."""

    case_id: str | None = None
    evaluated: bool = True
    match: bool = False
    expected_sql: str | None = None
    generated_sql: str | None = None
    normalized_expected_sql: str | None = None
    normalized_generated_sql: str | None = None
    expected_tables: list[str] = Field(default_factory=list)
    generated_tables: list[str] = Field(default_factory=list)
    tables_match: bool = False
    error: str | None = None


class SQLAccuracySummary(BaseModel):
    """Aggregate deterministic SQL-accuracy results."""

    evaluated_cases: int = 0
    matched_cases: int = 0
    accuracy: float = 0.0
    results: list[SQLComparisonResult] = Field(default_factory=list)


class SQLAccuracyEvaluator:
    """Evaluate SQL using SQLGlot AST normalization.

    This evaluator intentionally does not compare raw SQL strings. SQLGlot
    parses both statements and renders a normalized PostgreSQL representation,
    which removes differences such as whitespace and keyword casing while
    preserving query structure, expressions, joins, filters, grouping,
    ordering, limits, and aliases.

    This is structural SQL accuracy, not a claim of full semantic equivalence.
    More advanced semantic equivalence belongs in the later semantic-evaluation
    milestone.
    """

    DIALECT = "postgres"

    def evaluate(
        self,
        expected_sql: str | None,
        generated_sql: str | None,
        *,
        case_id: str | None = None,
        expected_tables: list[str] | None = None,
    ) -> SQLComparisonResult:
        """Compare one generated SQL statement against expected SQL."""

        if expected_sql is None:
            return SQLComparisonResult(
                case_id=case_id,
                evaluated=False,
                match=False,
                expected_sql=None,
                generated_sql=generated_sql,
                error="No expected SQL is defined for this evaluation case.",
            )

        if not generated_sql or not generated_sql.strip():
            return SQLComparisonResult(
                case_id=case_id,
                expected_sql=expected_sql,
                generated_sql=generated_sql,
                error="Generated SQL is empty.",
            )

        try:
            expected_expression = sqlglot.parse_one(
                expected_sql,
                read=self.DIALECT,
            )
            generated_expression = sqlglot.parse_one(
                generated_sql,
                read=self.DIALECT,
            )

            normalized_expected = expected_expression.sql(
                dialect=self.DIALECT,
                normalize=True,
            )
            normalized_generated = generated_expression.sql(
                dialect=self.DIALECT,
                normalize=True,
            )

            expected_table_names = self._extract_tables(expected_expression)
            generated_table_names = self._extract_tables(generated_expression)

            if expected_tables is not None:
                expected_table_names = sorted(
                    {table.lower() for table in expected_tables}
                )

            tables_match = expected_table_names == generated_table_names
            match = normalized_expected == normalized_generated

            return SQLComparisonResult(
                case_id=case_id,
                expected_sql=expected_sql,
                generated_sql=generated_sql,
                normalized_expected_sql=normalized_expected,
                normalized_generated_sql=normalized_generated,
                expected_tables=expected_table_names,
                generated_tables=generated_table_names,
                tables_match=tables_match,
                match=match,
            )
        except sqlglot.errors.ParseError as exc:
            return SQLComparisonResult(
                case_id=case_id,
                expected_sql=expected_sql,
                generated_sql=generated_sql,
                error=f"SQL parsing failed: {exc}",
            )
        except Exception as exc:
            return SQLComparisonResult(
                case_id=case_id,
                expected_sql=expected_sql,
                generated_sql=generated_sql,
                error=f"SQL evaluation failed: {exc}",
            )

    def evaluate_case(
        self,
        case: EvaluationCase,
        generated_sql: str | None,
    ) -> SQLComparisonResult:
        """Evaluate generated SQL using one dataset case as ground truth."""

        return self.evaluate(
            case.expected_sql,
            generated_sql,
            case_id=case.case_id,
            expected_tables=case.expected_tables or None,
        )

    def summarize(
        self,
        results: list[SQLComparisonResult],
    ) -> SQLAccuracySummary:
        """Calculate accuracy only over cases that contain expected SQL."""

        evaluated = [result for result in results if result.evaluated]
        matched = [result for result in evaluated if result.match]
        accuracy = len(matched) / len(evaluated) if evaluated else 0.0

        return SQLAccuracySummary(
            evaluated_cases=len(evaluated),
            matched_cases=len(matched),
            accuracy=accuracy,
            results=results,
        )

    def evaluate_cases(
        self,
        cases: list[EvaluationCase],
        generated_sql_by_case: dict[str, str | None],
    ) -> SQLAccuracySummary:
        """Evaluate multiple dataset cases from generated SQL by case ID."""

        results = [
            self.evaluate_case(case, generated_sql_by_case.get(case.case_id))
            for case in cases
        ]
        return self.summarize(results)

    @staticmethod
    def _extract_tables(expression: exp.Expression) -> list[str]:
        """Extract physical table names from a parsed SQL expression."""

        tables: set[str] = set()
        for table in expression.find_all(exp.Table):
            name = table.name
            if name:
                tables.add(name.lower())
        return sorted(tables)


def evaluate_sql(
    expected_sql: str | None,
    generated_sql: str | None,
) -> SQLComparisonResult:
    """Small functional API for callers that do not need an evaluator object."""

    return SQLAccuracyEvaluator().evaluate(expected_sql, generated_sql)
