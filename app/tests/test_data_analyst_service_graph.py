from unittest.mock import Mock

from agents.analytical_context_extractor import AnalyticalContextExtractor
from agents.clarification_resolver import ClarificationResolver
from agents.follow_up_resolver import FollowUpResolver
from models.agent import AnalyticsResult, SQLResult
from models.clarification import ClarificationResult
from models.request import DataAnalystRequest
from models.state import AgentState
from services.conversation_service import ConversationService
from services.data_analyst_service import DataAnalystService
from services.question_validator import QuestionValidator
from services.observability import ObservabilityService
from observability.metrics import metrics_registry

class FakeGraph:
    def __init__(self, state: AgentState):
        self.state = state
        self.calls = []

    def run(self, question, analytical_context=None):
        self.calls.append((question, analytical_context))
        return self.state


def create_service(graph):
    return DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=ConversationService(),
        clarification_resolver=ClarificationResolver(),
        follow_up_resolver=FollowUpResolver(),
        analytical_context_extractor=AnalyticalContextExtractor(),
    )


def successful_state(question="Show the top 5 products by revenue"):
    return AgentState(
        question=question,
        answer="The top 5 products are...",
        sql=SQLResult(
            success=True,
            sql="SELECT ...",
        ),
        analytics=AnalyticsResult(
            success=True,
            analysis={"columns": ["product_name"], "rows": [["Bike"]]},
        ),
        execution_trace=[
            {
                "stage": "completed",
                "status": "success",
                "attempt": 0,
                "message": "completed",
            }
        ],
        success=True,
    )


def test_service_uses_langgraph_for_normal_request():
    graph = FakeGraph(successful_state())
    service = create_service(graph)

    response = service.ask(
        DataAnalystRequest(question="Show the top 5 products by revenue")
    )

    assert response.success is True
    assert len(graph.calls) == 1
    question, context = graph.calls[0]
    assert question == "Show the top 5 products by revenue"
    assert context is not None
    assert context.metric == "revenue"
    assert context.entity == "product"
    assert context.limit == 5
    assert response.execution_trace == graph.state.execution_trace
    assert response.execution_summary is not None
    assert response.execution_summary.successful is True


def test_service_preserves_clarification_flow_before_using_langgraph():
    clarification_state = AgentState(
        question="Show revenue",
        clarification=ClarificationResult(
            needs_clarification=True,
            question="Which entity do you mean?",
            options=["products", "customers"],
        ),
        execution_trace=[
            {
                "stage": "clarification",
                "status": "success",
                "attempt": 0,
                "message": "clarification required",
            }
        ],
        success=True,
    )
    graph = FakeGraph(clarification_state)
    clarification_resolver = Mock(spec=ClarificationResolver)
    clarification_resolver.resolve.return_value = "Show revenue for products"

    service = DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=ConversationService(),
        clarification_resolver=clarification_resolver,
        follow_up_resolver=FollowUpResolver(),
        analytical_context_extractor=AnalyticalContextExtractor(),
    )

    first = service.ask(DataAnalystRequest(question="Show revenue"))

    assert first.success is True
    assert first.needs_clarification is True
    assert first.clarification_question == "Which entity do you mean?"
    assert len(graph.calls) == 1

    conversation_id = first.conversation_id
    graph.state = successful_state("Show revenue for products")

    second = service.ask(
        DataAnalystRequest(
            question="products",
            conversation_id=conversation_id,
        )
    )

    assert second.success is True
    assert second.needs_clarification is False
    assert len(graph.calls) == 2
    assert graph.calls[1][0] == "Show revenue for products"


def test_service_preserves_follow_up_resolution_before_using_langgraph():
    graph = FakeGraph(successful_state())
    conversation_service = ConversationService()
    follow_up_resolver = Mock(spec=FollowUpResolver)
    follow_up_resolver.resolve.return_value = "Show the bottom 3 products by revenue"

    service = DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=conversation_service,
        clarification_resolver=ClarificationResolver(),
        follow_up_resolver=follow_up_resolver,
        analytical_context_extractor=AnalyticalContextExtractor(),
    )

    first = service.ask(
        DataAnalystRequest(question="Show the top 5 products by revenue")
    )

    second = service.ask(
        DataAnalystRequest(
            question="bottom 3",
            conversation_id=first.conversation_id,
        )
    )

    assert second.success is True
    assert len(graph.calls) == 2
    assert graph.calls[1][0] == "Show the bottom 3 products by revenue"
    follow_up_resolver.resolve.assert_called_once()


def test_unrelated_question_resets_resolved_question_and_analytical_context():
    graph = FakeGraph(successful_state())
    service = create_service(graph)

    first = service.ask(DataAnalystRequest(
        question="Show the top 5 products by revenue"
    ))
    second = service.ask(DataAnalystRequest(
        question="How many orders were placed in 2025?",
        conversation_id=first.conversation_id,
    ))

    assert second.success is True
    assert graph.calls[1][0] == "How many orders were placed in 2025?"
    context = graph.calls[1][1]
    assert context.entity == "order"
    assert context.metric is None
    assert context.limit is None
    assert context.time_range["year"] == 2025

    conversation = service.conversation_service.get(first.conversation_id)
    assert conversation.resolved_question == "How many orders were placed in 2025?"


def test_legitimate_follow_up_preserves_analytical_context():
    graph = FakeGraph(successful_state())
    service = create_service(graph)

    first = service.ask(DataAnalystRequest(
        question="Show the top 5 products by revenue"
    ))
    second = service.ask(DataAnalystRequest(
        question="What about quantity?",
        conversation_id=first.conversation_id,
    ))

    assert second.success is True
    question, context = graph.calls[1]
    assert question == "Show the top 5 products by quantity"
    assert context.entity == "product"
    assert context.metric == "quantity"
    assert context.limit == 5


def test_service_activates_observability_context_during_graph_run():
    from services.observability import (
        ObservabilityContext,
        _CURRENT_CONTEXT,
    )

    graph = FakeGraph(successful_state())
    original_run = graph.run
    observed_contexts = []

    def run_with_context_check(question, analytical_context=None):
        context = _CURRENT_CONTEXT.get()
        observed_contexts.append(context)

        assert isinstance(context, ObservabilityContext)
        assert context.conversation_id == "conversation-observability-test"

        return original_run(question, analytical_context)

    graph.run = run_with_context_check
    service = create_service(graph)

    response = service.ask(
        DataAnalystRequest(
            question="Show the top 5 products by revenue",
            conversation_id="conversation-observability-test",
        )
    )

    assert response.success is True
    assert len(observed_contexts) == 1
    assert _CURRENT_CONTEXT.get() is None


def test_graph_execution_records_success_metrics():
    metrics_registry.reset()
    try:
        graph = FakeGraph(successful_state())
        service = create_service(graph)

        state = service._run_graph(
            "Show the top 5 products by revenue",
            analytical_context=None,
            conversation_id="graph-metrics-success",
        )

        snapshot = metrics_registry.snapshot()

        assert state.success is True
        assert snapshot["counters"]["agent.graph_executions"] == 1
        assert snapshot["counters"]["agent.graph_successes"] == 1
        assert snapshot["counters"].get("agent.graph_failures", 0) == 0
        assert snapshot["timings"]["agent.graph_execution_ms"]["count"] == 1
    finally:
        metrics_registry.reset()


def test_graph_execution_records_failure_metrics():
    metrics_registry.reset()

    class FailingGraph(FakeGraph):
        def run(self, question, analytical_context=None):
            raise RuntimeError("simulated graph failure")

    try:
        graph = FailingGraph(successful_state())
        service = create_service(graph)

        import pytest

        with pytest.raises(RuntimeError, match="simulated graph failure"):
            service._run_graph(
                "Show the top 5 products by revenue",
                analytical_context=None,
                conversation_id="graph-metrics-failure",
            )

        snapshot = metrics_registry.snapshot()

        assert snapshot["counters"]["agent.graph_executions"] == 1
        assert snapshot["counters"].get("agent.graph_successes", 0) == 0
        assert snapshot["counters"]["agent.graph_failures"] == 1
        assert snapshot["timings"]["agent.graph_execution_ms"]["count"] == 1
    finally:
        metrics_registry.reset()

from models.agent import AnalyticsResult, SQLResult
from models.request import DataAnalystRequest
from models.state import AgentState


def test_service_returns_fallback_answer_with_failed_status():
    fallback = (
        "The query returned the following results:\n"
        "- product_name: Bike"
    )
    state = AgentState(
        question="Show products",
        answer=fallback,
        sql=SQLResult(success=True, sql="SELECT product_name FROM products"),
        analytics=AnalyticsResult(
            success=True,
            analysis={
                "columns": ["product_name"],
                "rows": [["Bike"]],
            },
        ),
        success=False,
        error="Answer generation failed: provider rate limit",
        execution_trace=[
            {
                "stage": "answer_generation",
                "status": "failed",
                "attempt": 0,
                "message": "Answer generation failed.",
                "metadata": {"exception_type": "RateLimitError"},
            }
        ],
    )

    service = create_service(FakeGraph(state))
    response = service.ask(
        DataAnalystRequest(question="Show products")
    )

    assert response.success is False
    assert response.answer == fallback
    assert "rate limit" in str(response.error).lower()
    assert response.execution_trace[-1]["status"] == "failed"
