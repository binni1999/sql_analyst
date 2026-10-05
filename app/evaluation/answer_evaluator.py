from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from evaluation.models import EvaluationCase


class AnswerComparisonResult(BaseModel):
    """Deterministic answer-correctness result for one evaluation case."""

    case_id: str | None = None
    evaluated: bool = True
    match: bool = False
    generated_answer: str | None = None
    expected_answer: str | None = None

    required_concepts: list[str] = Field(default_factory=list)
    matched_concepts: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    concept_coverage: float = 0.0

    expected_result_contract: dict[str, Any] | None = None
    result_contract_checks: dict[str, bool] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class AnswerAccuracySummary(BaseModel):
    """Aggregate answer-correctness results."""

    evaluated_cases: int = 0
    matched_cases: int = 0
    accuracy: float = 0.0
    results: list[AnswerComparisonResult] = Field(default_factory=list)


class AnswerCorrectnessEvaluator:
    """Evaluate whether a final natural-language answer satisfies its contract.

    This is intentionally deterministic. The current evaluation dataset contains
    descriptive answer contracts rather than fixed database values, so this
    evaluator checks required semantic concepts and result-contract references.
    It does not pretend to verify numeric correctness when the dataset does not
    provide expected numeric values.
    """

    _STOP_WORDS = {
        "a", "an", "the", "and", "or", "of", "by", "for", "to", "from",
        "in", "on", "with", "after", "before", "only", "as", "such", "was",
        "were", "is", "are", "be", "that", "this", "user", "value", "values",
        "calculated", "generated", "placed", "defined", "metric",
    }

    _SYNONYMS = {
        "highest": {"highest", "top", "largest", "greatest", "descending", "desc"},
        "lowest": {"lowest", "bottom", "smallest", "ascending", "asc"},
        "revenue": {"revenue", "sales", "salesvalue"},
        "quantity": {"quantity", "units", "unitssold", "totalunits"},
        "products": {"product", "products", "items"},
        "delivered": {"delivered", "delivery"},
        "discount": {"discount", "discounted"},
        "year2025": {"2025"},
        "five": {"5", "five", "top5", "topfive"},
        "rating": {"rating", "ratings", "average", "reviewrating"},
    }

    def evaluate_case(
        self,
        case: EvaluationCase,
        generated_answer: str | None,
    ) -> AnswerComparisonResult:
        if case.expected_answer is None:
            return AnswerComparisonResult(
                case_id=case.case_id,
                evaluated=False,
                generated_answer=generated_answer,
                expected_answer=None,
                expected_result_contract=case.expected_result,
                errors=["No answer ground truth is defined for this case."],
            )

        if not generated_answer or not generated_answer.strip():
            return AnswerComparisonResult(
                case_id=case.case_id,
                generated_answer=generated_answer,
                expected_answer=case.expected_answer,
                expected_result_contract=case.expected_result,
                errors=["Generated answer is empty."],
            )

        required = self._required_concepts(case)
        matched = [
            concept
            for concept in required
            if self._concept_present(concept, generated_answer)
        ]
        missing = [concept for concept in required if concept not in matched]
        coverage = len(matched) / len(required) if required else 1.0

        contract_checks = self._result_contract_checks(case, generated_answer)
        errors = [
            f"Missing answer concept: {concept}."
            for concept in missing
        ]
        errors.extend(
            f"Answer result-contract requirement failed: {name}."
            for name, passed in contract_checks.items()
            if not passed
        )

        # A contract is considered satisfied only when all required concepts
        # and all explicitly checkable result references are present.
        match = not errors

        return AnswerComparisonResult(
            case_id=case.case_id,
            generated_answer=generated_answer,
            expected_answer=case.expected_answer,
            required_concepts=required,
            matched_concepts=matched,
            missing_concepts=missing,
            concept_coverage=coverage,
            expected_result_contract=case.expected_result,
            result_contract_checks=contract_checks,
            errors=errors,
            match=match,
        )

    def summarize(
        self,
        results: list[AnswerComparisonResult],
    ) -> AnswerAccuracySummary:
        evaluated = [result for result in results if result.evaluated]
        matched = [result for result in evaluated if result.match]
        return AnswerAccuracySummary(
            evaluated_cases=len(evaluated),
            matched_cases=len(matched),
            accuracy=len(matched) / len(evaluated) if evaluated else 0.0,
            results=results,
        )

    def evaluate_cases(
        self,
        cases: list[EvaluationCase],
        generated_answers_by_case: dict[str, str | None],
    ) -> AnswerAccuracySummary:
        results = [
            self.evaluate_case(
                case,
                generated_answers_by_case.get(case.case_id),
            )
            for case in cases
        ]
        return self.summarize(results)

    def _required_concepts(self, case: EvaluationCase) -> list[str]:
        """Build a compact semantic contract from the dataset ground truth."""

        concepts: list[str] = []
        answer = self._normalize(case.expected_answer or "")

        # Preserve concepts explicitly stated by the expected answer.
        if "revenue" in answer or case.expected_metric == "revenue":
            concepts.append("revenue")
        if "quantity" in answer or "units" in answer or case.expected_metric == "quantity":
            concepts.append("quantity")
        if "product" in answer:
            concepts.append("products")
        if "delivered" in answer:
            concepts.append("delivered")
        if "discount" in answer:
            concepts.append("discount")
        if "highest" in answer or "lowest" in answer:
            concepts.append("highest" if "highest" in answer else "lowest")

        contract = case.expected_result or {}
        if contract.get("row_count") == 5 or contract.get("limit") == 5:
            concepts.append("five")
        time_filter = contract.get("time_filter") or {}
        if time_filter.get("year"):
            concepts.append(f"year{time_filter['year']}")
        if contract.get("ordering"):
            ordering = str(contract["ordering"]).lower()
            if ordering.endswith("_desc") and "highest" not in concepts:
                concepts.append("highest")
            if ordering.endswith("_asc") and "lowest" not in concepts:
                concepts.append("lowest")

        # Rating is useful for the evaluation dataset even though it is not yet
        # represented in METRIC_METADATA.
        if "rating" in answer or case.expected_metric == "rating":
            concepts.append("rating")

        return list(dict.fromkeys(concepts))

    def _concept_present(self, concept: str, answer: str) -> bool:
        normalized = self._normalize(answer)
        if concept.startswith("year"):
            return concept[4:] in normalized

        candidates = self._SYNONYMS.get(concept, {concept})
        tokens = set(self._tokens(normalized))
        compact = normalized.replace(" ", "")
        return any(candidate in tokens or candidate in compact for candidate in candidates)

    def _result_contract_checks(
        self,
        case: EvaluationCase,
        generated_answer: str,
    ) -> dict[str, bool]:
        """Check only result-contract facts that can be supported by text."""

        contract = case.expected_result or {}
        checks: dict[str, bool] = {}
        normalized = self._normalize(generated_answer)

        if contract.get("row_count") == 5 or contract.get("limit") == 5:
            checks["row_count_or_limit_5"] = self._concept_present("five", generated_answer)

        if contract.get("ordering"):
            ordering = str(contract["ordering"]).lower()
            if ordering.endswith("_desc"):
                checks["descending_order"] = self._concept_present("highest", generated_answer)
            elif ordering.endswith("_asc"):
                checks["ascending_order"] = self._concept_present("lowest", generated_answer)

        time_filter = contract.get("time_filter") or {}
        if time_filter.get("year"):
            checks[f"year_{time_filter['year']}"] = str(time_filter["year"]) in normalized

        if contract.get("filter") and "delivered" in str(contract["filter"]).lower():
            checks["delivered_filter"] = self._concept_present("delivered", generated_answer)

        return checks

    @classmethod
    def _normalize(cls, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        return [
            token
            for token in cls._normalize(text).split()
            if token not in cls._STOP_WORDS
        ]


def evaluate_answer(
    case: EvaluationCase,
    generated_answer: str | None,
) -> AnswerComparisonResult:
    """Small functional API for one answer evaluation."""

    return AnswerCorrectnessEvaluator().evaluate_case(case, generated_answer)
