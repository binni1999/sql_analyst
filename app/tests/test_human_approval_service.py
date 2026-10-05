from agents.analytical_context_extractor import AnalyticalContextExtractor
from agents.clarification_resolver import ClarificationResolver
from agents.follow_up_resolver import FollowUpResolver
from models.agent import AnalyticsResult, SQLResult
from models.human_approval import HumanApprovalStatus, RiskAssessment
from models.request import DataAnalystRequest
from models.state import AgentState, AgentStep
from services.conversation_service import ConversationService
from services.data_analyst_service import DataAnalystService
from services.question_validator import QuestionValidator


class StubGraph:
    def __init__(self):
        self.resume_calls = []

    def run(self, question, analytical_context=None):
        state = AgentState(question=question)
        state.sql = SQLResult(success=True, sql="SELECT COUNT(*) FROM orders")
        state.risk_assessment = RiskAssessment(
            is_risky=True,
            risk_level="medium",
            reasons=["Unfiltered aggregation may scan a large table."],
            checks=["aggregation_scan"],
        )
        state.human_approval_required = True
        state.human_approval_status = HumanApprovalStatus.PENDING
        state.human_approval_question = "Approve execution?"
        state.current_step = AgentStep.HUMAN_APPROVAL
        return state

    def resume_after_human_approval(self, state, approved):
        self.resume_calls.append(approved)
        if not approved:
            state.mark_failure("Human approval rejected SQL execution.")
            state.human_approval_status = HumanApprovalStatus.REJECTED
            return state
        state.human_approval_required = False
        state.human_approval_status = HumanApprovalStatus.APPROVED
        state.analytics = AnalyticsResult(
            success=True,
            analysis={"row_count": 1},
        )
        state.answer = "There is 1 row."
        state.current_step = AgentStep.COMPLETED
        state.mark_success()
        return state


def make_service(graph):
    return DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=ConversationService(),
        clarification_resolver=ClarificationResolver(),
        follow_up_resolver=FollowUpResolver(),
        analytical_context_extractor=AnalyticalContextExtractor(),
    )


def test_service_persists_pending_human_approval():
    graph = StubGraph()
    service = make_service(graph)

    response = service.ask(
        DataAnalystRequest(question="Run expensive order aggregation")
    )

    assert response.success is True
    assert response.needs_human_approval is True
    assert response.sql == "SELECT COUNT(*) FROM orders"
    assert response.risk_assessment["risk_level"] == "medium"

    conversation = service.conversation_service.get(response.conversation_id)
    assert conversation.waiting_for_human_approval is True
    assert conversation.pending_agent_state is not None


def test_service_resumes_after_human_approval():
    graph = StubGraph()
    service = make_service(graph)

    first = service.ask(
        DataAnalystRequest(question="Run expensive order aggregation")
    )

    second = service.ask(
        DataAnalystRequest(
            question="Approve",
            conversation_id=first.conversation_id,
            human_approval=True,
        )
    )

    assert graph.resume_calls == [True]
    assert second.success is True
    assert second.needs_human_approval is False
    assert second.answer == "There is 1 row."

    conversation = service.conversation_service.get(first.conversation_id)
    assert conversation.waiting_for_human_approval is False
    assert conversation.pending_agent_state is None


def test_service_rejects_human_approval_without_executing():
    graph = StubGraph()
    service = make_service(graph)

    first = service.ask(
        DataAnalystRequest(question="Run expensive order aggregation")
    )

    second = service.ask(
        DataAnalystRequest(
            question="Reject",
            conversation_id=first.conversation_id,
            human_approval=False,
        )
    )

    assert graph.resume_calls == [False]
    assert second.success is False
    assert second.needs_human_approval is False
    assert second.error == "Human approval rejected SQL execution."
