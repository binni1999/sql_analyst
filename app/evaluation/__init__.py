"""Evaluation framework for the multi-agent SQL/data analyst."""

from evaluation.dataset import EvaluationDataset, load_evaluation_dataset
from evaluation.models import EvaluationCase, EvaluationTurn
from evaluation.answer_evaluator import (
    AnswerAccuracySummary,
    AnswerComparisonResult,
    AnswerCorrectnessEvaluator,
    evaluate_answer,
)
from evaluation.behavior_evaluator import (
    AgentBehaviorCaseResult,
    AgentBehaviorObservation,
    AgentBehaviorSummary,
    evaluate_agent_behavior,
    evaluate_agent_behaviors,
)
from evaluation.harness import (
    DataAnalystServiceRunner,
    EvaluationCaseResult,
    EvaluationHarness,
    EvaluationRuntime,
    EvaluationSummary,
    run_evaluation,
)
from evaluation.semantic_evaluator import (
    SemanticAccuracyEvaluator,
    SemanticAccuracySummary,
    SemanticComparisonResult,
)

__all__ = [
    "EvaluationCase",
    "EvaluationTurn",
    "EvaluationDataset",
    "load_evaluation_dataset",
    "AnswerAccuracySummary",
    "AnswerComparisonResult",
    "AnswerCorrectnessEvaluator",
    "evaluate_answer",
    "SemanticAccuracyEvaluator",
    "SemanticAccuracySummary",
    "SemanticComparisonResult",
    "AgentBehaviorCaseResult",
    "AgentBehaviorObservation",
    "AgentBehaviorSummary",
    "DataAnalystServiceRunner",
    "EvaluationCaseResult",
    "EvaluationHarness",
    "EvaluationRuntime",
    "EvaluationSummary",
    "run_evaluation",
    "evaluate_agent_behavior",
    "evaluate_agent_behaviors",
]
