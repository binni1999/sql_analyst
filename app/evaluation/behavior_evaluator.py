from __future__ import annotations

from typing import Any, Iterable

from evaluation.models import EvaluationCase
from models.conversation import ConversationState
from models.human_approval import HumanApprovalStatus
from models.state import AgentState


_ROUTE_STAGE_MAP = {
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
}


class AgentBehaviorObservation:
    """Normalized runtime facts consumed by behavior evaluators.

    The evaluator intentionally accepts plain runtime facts rather than
    executing the agent itself. This keeps evaluation deterministic and lets
    the same evaluator score real runs, replayed traces, or unit-test fixtures.
    """

    def __init__(
        self,
        *,
        intent: str | None = None,
        clarification_required: bool = False,
        clarification_question: str | None = None,
        business_knowledge_document_ids: Iterable[str] = (),
        tools_used: Iterable[str] = (),
        route: Iterable[str] = (),
        memory_turn_count: int | None = None,
        used_previous_context: bool = False,
        human_approval_required: bool = False,
        human_approval_status: str | None = None,
        outcome: str | None = None,
        execution_trace: Iterable[dict[str, Any]] = (),
    ):
        self.intent = intent
        self.clarification_required = clarification_required
        self.clarification_question = clarification_question
        self.business_knowledge_document_ids = list(
            business_knowledge_document_ids
        )
        self.tools_used = list(tools_used)
        self.route = list(route)
        self.memory_turn_count = memory_turn_count
        self.used_previous_context = used_previous_context
        self.human_approval_required = human_approval_required
        self.human_approval_status = human_approval_status
        self.outcome = outcome
        self.execution_trace = list(execution_trace)

    @classmethod
    def from_agent_state(
        cls,
        state: AgentState,
        conversation: ConversationState | None = None,
    ) -> "AgentBehaviorObservation":
        trace = list(state.execution_trace)

        documents: list[str] = []
        if state.business_knowledge:
            documents = [
                match.document.document_id
                for match in state.business_knowledge.matches
            ]

        tools = _extract_tools(trace)
        route = _extract_route(trace)

        memory_turn_count = None
        used_previous_context = False
        if conversation is not None:
            memory_turn_count = conversation.memory.turn_count
            used_previous_context = (
                conversation.memory.turn_count > 0
                or bool(conversation.memory.recent_resolved_questions)
            )

        clarification_required = bool(
            state.clarification
            and state.clarification.needs_clarification
        )

        if state.human_approval_status == HumanApprovalStatus.PENDING:
            outcome = "human_approval"
        elif clarification_required:
            outcome = "clarification"
        elif state.success:
            outcome = "execute_query"
        elif state.error:
            outcome = "reject_or_explain_unsupported"
        else:
            outcome = None

        return cls(
            intent=(
                state.intent.value
                if hasattr(state.intent, "value")
                else str(state.intent)
            ),
            clarification_required=clarification_required,
            clarification_question=(
                state.clarification.question
                if state.clarification
                else None
            ),
            business_knowledge_document_ids=documents,
            tools_used=tools,
            route=route,
            memory_turn_count=memory_turn_count,
            used_previous_context=used_previous_context,
            human_approval_required=state.human_approval_required,
            human_approval_status=state.human_approval_status.value,
            outcome=outcome,
            execution_trace=trace,
        )


class AgentBehaviorCaseResult:
    """Per-case behavior evaluation result."""

    def __init__(
        self,
        case_id: str,
        evaluated: bool,
        passed: bool,
        checks: dict[str, bool],
        failures: list[str],
    ):
        self.case_id = case_id
        self.evaluated = evaluated
        self.passed = passed
        self.checks = checks
        self.failures = failures

    def model_dump(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "evaluated": self.evaluated,
            "passed": self.passed,
            "checks": self.checks,
            "failures": self.failures,
        }


class AgentBehaviorSummary:
    """Aggregate behavior-evaluation metrics."""

    def __init__(self, results: list[AgentBehaviorCaseResult]):
        self.results = results
        evaluated = [result for result in results if result.evaluated]
        self.evaluated_cases = len(evaluated)
        self.passed_cases = sum(result.passed for result in evaluated)
        self.accuracy = (
            self.passed_cases / self.evaluated_cases
            if self.evaluated_cases
            else 0.0
        )

        self.routing_accuracy = _dimension_accuracy(results, "routing")
        self.tool_selection_accuracy = _dimension_accuracy(
            results, "tool_selection"
        )
        self.clarification_accuracy = _dimension_accuracy(
            results, "clarification"
        )
        self.business_knowledge_accuracy = _dimension_accuracy(
            results, "business_knowledge"
        )
        self.memory_accuracy = _dimension_accuracy(results, "memory")
        self.human_approval_accuracy = _dimension_accuracy(
            results, "human_approval"
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "evaluated_cases": self.evaluated_cases,
            "passed_cases": self.passed_cases,
            "accuracy": self.accuracy,
            "routing_accuracy": self.routing_accuracy,
            "tool_selection_accuracy": self.tool_selection_accuracy,
            "clarification_accuracy": self.clarification_accuracy,
            "business_knowledge_accuracy": self.business_knowledge_accuracy,
            "memory_accuracy": self.memory_accuracy,
            "human_approval_accuracy": self.human_approval_accuracy,
            "results": [result.model_dump() for result in self.results],
        }


def evaluate_agent_behavior(
    case: EvaluationCase,
    observation: AgentBehaviorObservation,
) -> AgentBehaviorCaseResult:
    """Evaluate the behavior contract for one evaluation case."""

    behavior = case.expected_behavior
    if not behavior:
        return AgentBehaviorCaseResult(
            case_id=case.case_id,
            evaluated=False,
            passed=False,
            checks={},
            failures=[],
        )

    checks: dict[str, bool] = {}
    failures: list[str] = []

    expected_outcome = behavior.get("outcome")
    if expected_outcome is not None:
        checks["outcome"] = observation.outcome == expected_outcome
        if not checks["outcome"]:
            failures.append(
                f"Expected outcome '{expected_outcome}', "
                f"got '{observation.outcome}'."
            )

    if case.expected_intent is not None:
        expected_intent = (
            case.expected_intent.value
            if hasattr(case.expected_intent, "value")
            else str(case.expected_intent)
        )
        checks["intent"] = observation.intent == expected_intent
        if not checks["intent"]:
            failures.append(
                f"Expected intent '{expected_intent}', "
                f"got '{observation.intent}'."
            )

    if "clarification" in behavior:
        expected = bool(behavior["clarification"])
        checks["clarification"] = (
            observation.clarification_required == expected
        )
        if not checks["clarification"]:
            failures.append(
                f"Expected clarification={expected}, "
                f"got {observation.clarification_required}."
            )

    if "sql_generation" in behavior:
        expected = bool(behavior["sql_generation"])
        generated_sql = any(
            event.get("stage") == "sql_agent"
            and event.get("status") == "success"
            for event in observation.execution_trace
        )
        actual = generated_sql
        checks["sql_generation"] = actual == expected
        if not checks["sql_generation"]:
            failures.append(
                f"Expected sql_generation={expected}, got {actual}."
            )

    if "context_required" in behavior:
        expected = bool(behavior["context_required"])
        actual = bool(observation.used_previous_context)
        checks["context"] = actual == expected
        if not checks["context"]:
            failures.append(
                f"Expected previous-context usage={expected}, got {actual}."
            )

    if "uses_previous_context" in behavior:
        expected = bool(behavior["uses_previous_context"])
        actual = bool(observation.used_previous_context)
        checks["memory"] = actual == expected
        if not checks["memory"]:
            failures.append(
                f"Expected memory/context usage={expected}, got {actual}."
            )

    if "uses_memory" in behavior:
        expected = bool(behavior["uses_memory"])
        actual = (
            observation.memory_turn_count is not None
            and observation.memory_turn_count > 0
        )
        checks["memory_store"] = actual == expected
        if not checks["memory_store"]:
            failures.append(
                f"Expected memory usage={expected}, got {actual}."
            )

    if "business_definition_required" in behavior:
        expected = bool(behavior["business_definition_required"])
        actual = bool(observation.business_knowledge_document_ids)
        checks["business_knowledge"] = actual == expected
        if not checks["business_knowledge"]:
            failures.append(
                f"Expected business knowledge usage={expected}, got {actual}."
            )

    if case.expected_business_knowledge_documents:
        expected_docs = set(case.expected_business_knowledge_documents)
        actual_docs = set(observation.business_knowledge_document_ids)
        checks["business_knowledge_documents"] = expected_docs.issubset(
            actual_docs
        )
        if not checks["business_knowledge_documents"]:
            failures.append(
                f"Missing expected business-knowledge documents: "
                f"{sorted(expected_docs - actual_docs)}."
            )

    if case.expected_tools:
        expected_tools = set(case.expected_tools)
        actual_tools = set(observation.tools_used)
        checks["tool_selection"] = expected_tools == actual_tools
        if not checks["tool_selection"]:
            failures.append(
                f"Expected tools {sorted(expected_tools)}, "
                f"got {sorted(actual_tools)}."
            )

    if case.expected_route:
        expected_route = list(case.expected_route)
        actual_route = list(observation.route)
        checks["routing"] = _is_expected_route(
            expected_route, actual_route
        )
        if not checks["routing"]:
            failures.append(
                f"Expected route {expected_route}, got {actual_route}."
            )

    if "human_approval" in behavior:
        expected = bool(behavior["human_approval"])
        actual = observation.human_approval_required or (
            observation.human_approval_status == HumanApprovalStatus.PENDING.value
        )
        checks["human_approval"] = actual == expected
        if not checks["human_approval"]:
            failures.append(
                f"Expected human approval={expected}, got {actual}."
            )

    if "risk_type" in behavior:
        expected_risk = str(behavior["risk_type"])
        actual_risks = []
        for event in observation.execution_trace:
            if event.get("stage") == "human_approval":
                reasons = event.get("metadata", {}).get("reasons", [])
                actual_risks.extend(str(reason).lower() for reason in reasons)
        checks["risk_type"] = any(
            expected_risk.lower() in reason for reason in actual_risks
        ) or any(
            expected_risk.lower() in str(event.get("message", "")).lower()
            for event in observation.execution_trace
            if event.get("stage") == "human_approval"
        )
        if not checks["risk_type"]:
            failures.append(
                f"Expected risk type '{expected_risk}' was not observed."
            )

    passed = bool(checks) and all(checks.values())
    return AgentBehaviorCaseResult(
        case_id=case.case_id,
        evaluated=True,
        passed=passed,
        checks=checks,
        failures=failures,
    )


def evaluate_agent_behaviors(
    cases: Iterable[EvaluationCase],
    observations: dict[str, AgentBehaviorObservation],
) -> AgentBehaviorSummary:
    results = [
        evaluate_agent_behavior(case, observations[case.case_id])
        for case in cases
        if case.case_id in observations
    ]
    return AgentBehaviorSummary(results)


def _extract_tools(trace: Iterable[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for event in trace:
        if event.get("stage") != "tool_call":
            continue
        tool = event.get("metadata", {}).get("tool")
        if tool and tool not in tools:
            tools.append(str(tool))
    return tools


def _extract_route(trace: Iterable[dict[str, Any]]) -> list[str]:
    route: list[str] = []
    for event in trace:
        stage = event.get("stage")
        mapped = _ROUTE_STAGE_MAP.get(stage)
        if mapped and mapped not in route:
            route.append(mapped)
    return route


def _is_expected_route(expected: list[str], actual: list[str]) -> bool:
    """Require expected nodes in order while allowing extra implementation events."""
    if not expected:
        return True

    index = 0
    for stage in actual:
        if stage == expected[index]:
            index += 1
            if index == len(expected):
                return True
    return False


def _dimension_accuracy(
    results: list[AgentBehaviorCaseResult],
    dimension: str,
) -> float:
    checks: list[bool] = []
    for result in results:
        if not result.evaluated:
            continue
        if dimension in result.checks:
            checks.append(result.checks[dimension])
        elif dimension == "routing" and "routing" in result.checks:
            checks.append(result.checks["routing"])
        elif dimension == "tool_selection" and "tool_selection" in result.checks:
            checks.append(result.checks["tool_selection"])
        elif dimension == "clarification" and "clarification" in result.checks:
            checks.append(result.checks["clarification"])
        elif dimension == "business_knowledge" and (
            "business_knowledge" in result.checks
            or "business_knowledge_documents" in result.checks
        ):
            checks.append(
                all(
                    result.checks[name]
                    for name in (
                        "business_knowledge",
                        "business_knowledge_documents",
                    )
                    if name in result.checks
                )
            )
        elif dimension == "memory" and (
            "memory" in result.checks or "memory_store" in result.checks
        ):
            checks.append(
                all(
                    result.checks[name]
                    for name in ("memory", "memory_store")
                    if name in result.checks
                )
            )
        elif dimension == "human_approval" and (
            "human_approval" in result.checks
            or "risk_type" in result.checks
        ):
            checks.append(
                all(
                    result.checks[name]
                    for name in ("human_approval", "risk_type")
                    if name in result.checks
                )
            )

    return sum(checks) / len(checks) if checks else 0.0
