from langgraph.checkpoint.memory import InMemorySaver

from agents.clarification_agent import ClarificationAgent
from agents.intent_agent import IntentAgent
from graph.workflow import DataAnalystGraph
from models.agent import AnalyticsResult, MetadataResult, SQLResult
from models.human_approval import HumanApprovalStatus


class MockMetadataAgent:
    def run(self, state):
        state.metadata = MetadataResult(
            schemas=[],
            schema_text="TEST SCHEMA",
            metadata="TEST METADATA",
        )
        return state


class MockSQLAgent:
    def run(self, state):
        state.sql = SQLResult(
            success=True,
            sql="SELECT COUNT(*) FROM orders",
            attempts=1,
            errors=[],
        )
        return state


class MockAnalyticsAgent:
    def run(self, state):
        state.analytics = AnalyticsResult(
            success=True,
            analysis={"row_count": 1},
        )
        return state


class MockAnswerGenerator:
    def generate(self, question, analyzed_result):
        return "Test answer"


def create_graph(checkpointer=None):
    return DataAnalystGraph(
        intent_agent=IntentAgent(),
        clarification_agent=ClarificationAgent(),
        metadata_agent=MockMetadataAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator(),
        checkpointer=checkpointer,
    )


def test_checkpointed_graph_requires_conversation_id():
    graph = create_graph(InMemorySaver())

    try:
        graph.run("Show revenue")
    except ValueError as exc:
        assert "conversation_id is required" in str(exc)
    else:
        raise AssertionError("Expected conversation_id requirement")


def test_checkpointed_hitl_state_can_be_recovered_from_same_thread():
    checkpointer = InMemorySaver()
    graph = create_graph(checkpointer)

    pending = graph.run(
        "Show revenue",
        conversation_id="conversation-hitl-61",
    )

    assert pending.human_approval_status == HumanApprovalStatus.PENDING
    assert pending.human_approval_required is True

    recovered = graph.get_checkpoint_state("conversation-hitl-61")

    assert recovered is not None
    recovered_state = recovered["agent_state"]
    assert recovered_state.human_approval_status == HumanApprovalStatus.PENDING
    assert recovered_state.sql.sql == "SELECT COUNT(*) FROM orders"


def test_checkpointed_hitl_resumes_same_thread():
    checkpointer = InMemorySaver()
    graph = create_graph(checkpointer)

    pending = graph.run(
        "Show revenue",
        conversation_id="conversation-hitl-61",
    )

    approved = graph.resume_after_human_approval(
        pending,
        True,
        conversation_id="conversation-hitl-61",
    )

    assert approved.human_approval_status == HumanApprovalStatus.APPROVED
    assert approved.analytics is not None
    assert approved.answer == "Test answer"
    assert approved.success is True


def test_human_approval_survives_conversation_service_restart():
    from agents.analytical_context_extractor import AnalyticalContextExtractor
    from agents.clarification_resolver import ClarificationResolver
    from agents.follow_up_resolver import FollowUpResolver
    from models.request import DataAnalystRequest
    from services.conversation_service import ConversationService
    from services.data_analyst_service import DataAnalystService
    from services.question_validator import QuestionValidator

    checkpointer = InMemorySaver()
    graph = create_graph(checkpointer)

    first_service = DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=ConversationService(),
        clarification_resolver=ClarificationResolver(),
        follow_up_resolver=FollowUpResolver(),
        analytical_context_extractor=AnalyticalContextExtractor(),
    )

    first = first_service.ask(
        DataAnalystRequest(question="Show revenue")
    )

    assert first.needs_human_approval is True

    # Simulate a process restart: the in-memory ConversationService is gone,
    # but the LangGraph checkpoint store remains available.
    restarted_service = DataAnalystService(
        graph=graph,
        question_validator=QuestionValidator(),
        conversation_service=ConversationService(),
        clarification_resolver=ClarificationResolver(),
        follow_up_resolver=FollowUpResolver(),
        analytical_context_extractor=AnalyticalContextExtractor(),
    )

    resumed = restarted_service.ask(
        DataAnalystRequest(
            question="Approve",
            conversation_id=first.conversation_id,
            human_approval=True,
        )
    )

    print("\nRESUMED SUCCESS:", resumed.success)
    print("RESUMED ANSWER:", resumed.answer)
    print("RESUMED ERROR:", resumed.error)
    print("RESUMED SQL:", resumed.sql)
    print("RESUMED TRACE:", resumed.execution_trace)
    print("RESUMED SUMMARY:", resumed.execution_summary)

    assert resumed.success is True
    assert resumed.answer == "Test answer"
