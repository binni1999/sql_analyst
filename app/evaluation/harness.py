from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from evaluation.answer_evaluator import AnswerComparisonResult, AnswerCorrectnessEvaluator
from evaluation.behavior_evaluator import (
    AgentBehaviorCaseResult,
    AgentBehaviorObservation,
    evaluate_agent_behavior,
)
from evaluation.models import EvaluationCase, EvaluationDataset
from evaluation.semantic_evaluator import SemanticAccuracyEvaluator, SemanticComparisonResult
from evaluation.sql_evaluator import SQLAccuracyEvaluator, SQLComparisonResult
from models.request import DataAnalystRequest
from models.response import DataAnalystResponse


class EvaluationRunner(Protocol):
    """Runtime adapter used by the evaluation harness."""

    def ask(
        self,
        question: str,
        *,
        conversation_id: str,
        human_approval: bool | None = None,
    ) -> DataAnalystResponse:
        ...


class DataAnalystServiceRunner:
    """Adapt the production DataAnalystService to the evaluation harness."""

    def __init__(self, service):
        self.service = service

    def ask(
        self,
        question: str,
        *,
        conversation_id: str,
        human_approval: bool | None = None,
    ) -> DataAnalystResponse:
        request = DataAnalystRequest(
            question=question,
            conversation_id=conversation_id,
            human_approval=human_approval,
        )
        return self.service.ask(request)


class EvaluationRuntime(BaseModel):
    """Runtime output captured from one evaluation case."""

    case_id: str
    conversation_id: str
    final_question: str
    generated_sql: str | None = None
    generated_answer: str | None = None
    result: dict[str, Any] | None = None
    success: bool = False
    needs_clarification: bool = False
    needs_human_approval: bool = False
    execution_trace: list[dict[str, Any]] = Field(default_factory=list)
    total_duration_ms: float | None = None
    turns_executed: int = 0
    errors: list[str] = Field(default_factory=list)
    observation: Any = None


class EvaluationCaseResult(BaseModel):
    """Combined evaluation result for one dataset case."""

    case_id: str
    runtime: EvaluationRuntime
    sql: SQLComparisonResult | None = None
    semantic: SemanticComparisonResult | None = None
    answer: AnswerComparisonResult | None = None
    behavior: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        checks = [
            result.match
            for result in (self.sql, self.semantic, self.answer)
            if result is not None and result.evaluated
        ]
        if self.behavior is not None and self.behavior.get("evaluated", False):
            checks.append(bool(self.behavior.get("passed", False)))
        return all(checks) if checks else self.runtime.success


class EvaluationSummary(BaseModel):
    """Consolidated evaluation report for a dataset run."""

    dataset_id: str
    dataset_version: str
    evaluated_cases: int = 0
    passed_cases: int = 0
    accuracy: float = 0.0

    sql_evaluated_cases: int = 0
    sql_matched_cases: int = 0
    sql_accuracy: float = 0.0

    semantic_evaluated_cases: int = 0
    semantic_matched_cases: int = 0
    semantic_accuracy: float = 0.0

    answer_evaluated_cases: int = 0
    answer_matched_cases: int = 0
    answer_accuracy: float = 0.0

    behavior_evaluated_cases: int = 0
    behavior_passed_cases: int = 0
    behavior_accuracy: float = 0.0

    total_duration_ms: float = 0.0
    results: list[EvaluationCaseResult] = Field(default_factory=list)


@dataclass
class _CaseExecution:
    responses: list[DataAnalystResponse]
    conversation_id: str


class EvaluationHarness:
    """Run the evaluation dataset against the real agent runtime.

    The harness is deliberately separate from the evaluators. A runner executes
    the system; the existing SQL, semantic, answer, and behavior evaluators
    score the captured runtime output. This makes the same evaluators usable
    with the production service, replay fixtures, or another runner later.
    """

    def __init__(
        self,
        runner: EvaluationRunner,
        *,
        sql_evaluator: SQLAccuracyEvaluator | None = None,
        semantic_evaluator: SemanticAccuracyEvaluator | None = None,
        answer_evaluator: AnswerCorrectnessEvaluator | None = None,
    ):
        self.runner = runner
        self.sql_evaluator = sql_evaluator or SQLAccuracyEvaluator()
        self.semantic_evaluator = semantic_evaluator or SemanticAccuracyEvaluator()
        self.answer_evaluator = answer_evaluator or AnswerCorrectnessEvaluator()

    def run_case(self, case: EvaluationCase) -> EvaluationCaseResult:
        execution = self._execute_case(case)
        response = execution.responses[-1]
        runtime = self._build_runtime(case, execution)

        sql_result = self.sql_evaluator.evaluate_case(
            case,
            runtime.generated_sql,
        )
        semantic_result = self.semantic_evaluator.evaluate_case(
            case,
            runtime.generated_sql,
        )
        answer_result = self.answer_evaluator.evaluate_case(
            case,
            runtime.generated_answer,
        )

        behavior_result = None
        if runtime.observation is not None:
            behavior_result = evaluate_agent_behavior(
                case,
                runtime.observation,
            ).model_dump()

        return EvaluationCaseResult(
            case_id=case.case_id,
            runtime=runtime,
            sql=sql_result,
            semantic=semantic_result,
            answer=answer_result,
            behavior=behavior_result,
        )

    def run_dataset(self, dataset: EvaluationDataset) -> EvaluationSummary:
        results = [self.run_case(case) for case in dataset.cases]
        return self.summarize(dataset, results)

    @staticmethod
    def summarize(
        dataset: EvaluationDataset,
        results: list[EvaluationCaseResult],
    ) -> EvaluationSummary:
        sql_results = [
            result.sql
            for result in results
            if result.sql is not None and result.sql.evaluated
        ]
        semantic_results = [
            result.semantic
            for result in results
            if result.semantic is not None and result.semantic.evaluated
        ]
        answer_results = [
            result.answer
            for result in results
            if result.answer is not None and result.answer.evaluated
        ]
        behavior_results = [
            result.behavior
            for result in results
            if result.behavior is not None and result.behavior.get("evaluated", False)
        ]

        passed_cases = sum(result.passed for result in results)
        total_cases = len(results)

        sql_matched = sum(result.match for result in sql_results)
        semantic_matched = sum(result.match for result in semantic_results)
        answer_matched = sum(result.match for result in answer_results)
        behavior_passed = sum(result.get("passed", False) for result in behavior_results)

        return EvaluationSummary(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            evaluated_cases=total_cases,
            passed_cases=passed_cases,
            accuracy=passed_cases / total_cases if total_cases else 0.0,
            sql_evaluated_cases=len(sql_results),
            sql_matched_cases=sql_matched,
            sql_accuracy=sql_matched / len(sql_results) if sql_results else 0.0,
            semantic_evaluated_cases=len(semantic_results),
            semantic_matched_cases=semantic_matched,
            semantic_accuracy=(
                semantic_matched / len(semantic_results)
                if semantic_results else 0.0
            ),
            answer_evaluated_cases=len(answer_results),
            answer_matched_cases=answer_matched,
            answer_accuracy=(
                answer_matched / len(answer_results)
                if answer_results else 0.0
            ),
            behavior_evaluated_cases=len(behavior_results),
            behavior_passed_cases=behavior_passed,
            behavior_accuracy=(
                behavior_passed / len(behavior_results)
                if behavior_results else 0.0
            ),
            total_duration_ms=sum(
                result.runtime.total_duration_ms or 0.0
                for result in results
            ),
            results=results,
        )

    def _execute_case(self, case: EvaluationCase) -> _CaseExecution:
        conversation_id = f"evaluation-{case.case_id}-{uuid4().hex}"
        turns = case.conversation or [
            type("Turn", (), {"question": case.question})()
        ]

        responses: list[DataAnalystResponse] = []
        for index, turn in enumerate(turns):
            approval = None
            # The dataset currently uses the first HITL turn to evaluate the
            # pending approval behavior. Approval decisions can be supplied by
            # a custom runner when a future case explicitly requires a second
            # approval turn.
            response = self.runner.ask(
                turn.question,
                conversation_id=conversation_id,
                human_approval=approval,
            )
            responses.append(response)

            if response.needs_human_approval and index == len(turns) - 1:
                break

        return _CaseExecution(
            responses=responses,
            conversation_id=conversation_id,
        )

    @staticmethod
    def _build_runtime(
        case: EvaluationCase,
        execution: _CaseExecution,
    ) -> EvaluationRuntime:
        response = execution.responses[-1]
        summary = response.execution_summary
        trace = list(response.execution_trace or [])

        observation = _observation_from_response(
            response,
            trace,
            turn_count=len(execution.responses),
        )

        errors: list[str] = []
        if response.error:
            if isinstance(response.error, list):
                errors.extend(str(item) for item in response.error)
            else:
                errors.append(str(response.error))

        return EvaluationRuntime(
            case_id=case.case_id,
            conversation_id=execution.conversation_id,
            final_question=response.question,
            generated_sql=response.sql,
            generated_answer=response.answer,
            result=response.result,
            success=response.success,
            needs_clarification=response.needs_clarification,
            needs_human_approval=response.needs_human_approval,
            execution_trace=trace,
            total_duration_ms=(
                summary.total_duration_ms if summary is not None else None
            ),
            turns_executed=len(execution.responses),
            errors=errors,
            observation=observation,
        )


def _observation_from_response(
    response: DataAnalystResponse,
    trace: list[dict[str, Any]],
    *,
    turn_count: int,
) -> AgentBehaviorObservation:
    documents: list[str] = []
    tools: list[str] = []
    route: list[str] = []
    intent: str | None = None

    for event in trace:
        stage = str(event.get("stage", ""))
        metadata = event.get("metadata") or {}
        status = str(event.get("status", ""))
        message = str(event.get("message", ""))

        if stage == "business_knowledge" and status == "success":
            documents.extend(metadata.get("matched_document_ids") or [])

        if stage == "tool_call":
            tool = metadata.get("tool")
            if tool:
                tools.append(str(tool))

        if stage == "intent" and status == "success":
            lowered = message.lower()
            if "data_query" in lowered:
                intent = "data_query"
            elif "unknown" in lowered:
                intent = "unknown"

        route_stage = {
            "intent": "intent",
            "clarification": "clarification",
            "metadata": "metadata",
            "business_knowledge": "business_knowledge",
            "sql_agent": "sql",
            "risk_check": "risk_check",
            "human_approval": "human_approval",
            "analytics": "analytics",
            "answer_generation": "answer",
            "completed": "completed",
        }.get(stage)
        if route_stage and route_stage not in route:
            route.append(route_stage)

    if response.needs_human_approval:
        outcome = "human_approval"
    elif response.needs_clarification:
        outcome = "clarification"
    elif response.success and response.answer is not None:
        outcome = "execute_query"
    elif response.error:
        outcome = "reject_or_explain_unsupported"
    else:
        outcome = None

    risk_type = []
    for event in trace:
        if event.get("stage") == "human_approval":
            metadata = event.get("metadata") or {}
            risk_type.extend(metadata.get("reasons") or [])

    return AgentBehaviorObservation(
        intent=intent,
        clarification_required=response.needs_clarification,
        clarification_question=response.clarification_question,
        business_knowledge_document_ids=list(dict.fromkeys(documents)),
        tools_used=list(dict.fromkeys(tools)),
        route=route,
        memory_turn_count=max(turn_count - 1, 0),
        used_previous_context=turn_count > 1,
        human_approval_required=response.needs_human_approval,
        human_approval_status=(
            "pending" if response.needs_human_approval else None
        ),
        outcome=outcome,
        execution_trace=trace,
    )


def run_evaluation(
    dataset: EvaluationDataset,
    runner: EvaluationRunner,
) -> EvaluationSummary:
    """Convenience API for running one dataset."""

    return EvaluationHarness(runner).run_dataset(dataset)
