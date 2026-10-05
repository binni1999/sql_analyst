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
