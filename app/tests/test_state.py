from models.business_knowledge import (
    BusinessKnowledgeDocument,
    BusinessKnowledgeMatch,
    BusinessKnowledgeResult,
)
from models.state import AgentState, AgentStep
from models.intent import QuestionIntent

from models.agent import (
    MetadataResult,
    SQLResult,
    AnalyticsResult
)


def test_agent_state_initialization():

    state = AgentState(
        question="Show revenue"
    )

    assert state.question == "Show revenue"

    assert state.metadata is None
    assert state.business_knowledge is None

    assert state.sql is None

    assert state.analytics is None

    assert state.success is False

    assert state.error is None


def test_agent_state_with_agent_results():

    metadata = MetadataResult(
        schemas=[],
        schema_text="TEST SCHEMA",
        metadata="TEST METADATA"
    )

    sql = SQLResult(
        success=True,
        sql="SELECT 1",
        attempts=1,
        errors=[]
    )

    analytics = AnalyticsResult(
        success=True,
        analysis={
            "row_count": 1
        }
    )

    state = AgentState(
        question="Show revenue",
        metadata=metadata,
        sql=sql,
        analytics=analytics,
        success=True
    )

    assert state.question == "Show revenue"

    assert state.metadata is metadata

    assert state.sql is sql

    assert state.analytics is analytics

    assert state.success is True

    assert state.error is None


def test_agent_state_mark_success():

    state = AgentState(
        question="Show revenue"
    )

    state.error = "Temporary error"

    result = state.mark_success()

    assert result is state
    assert state.success is True
    assert state.error is None


def test_agent_state_mark_failure():

    state = AgentState(
        question="Show revenue"
    )

    result = state.mark_failure(
        "SQL generation failed"
    )

    assert result is state
    assert state.success is False
    assert state.error == (
        "SQL generation failed"
    )

def test_agent_state_with_answer():

    state = AgentState(
        question="Show revenue",
        answer="The top product generated $9,570 in revenue."
    )

    assert state.answer == (
        "The top product generated $9,570 in revenue."
    )

def test_agent_state_starts_initialized():

    state = AgentState(
        question="Show revenue"
    )

    assert state.current_step == AgentStep.INITIALIZED
    assert state.success is False
    assert state.error is None

def test_agent_state_failure_sets_failed_step():

    state = AgentState(
        question="Show revenue"
    )

    state.mark_failure(
        "Something went wrong"
    )

    assert state.current_step == AgentStep.FAILED
    assert state.success is False
    assert state.error == "Something went wrong"


def test_agent_state_defaults_to_unknown_intent():

    state = AgentState(
        question="Show revenue"
    )

    assert state.intent == QuestionIntent.UNKNOWN

def test_agent_state_can_store_data_query_intent():

    state = AgentState(
        question="Show revenue",
        intent=QuestionIntent.DATA_QUERY
    )

    assert state.intent == QuestionIntent.DATA_QUERY


def test_agent_state_execution_trace_defaults_to_empty_list():

    state = AgentState(
        question="Show revenue"
    )

    assert state.execution_trace == []


def test_agent_state_can_store_execution_trace():

    state = AgentState(
        question="Show revenue"
    )

    state.execution_trace.append(
        {
            "stage": "generation",
            "attempt": 0,
            "status": "success",
            "message": "SQL generated successfully.",
        }
    )

    assert len(state.execution_trace) == 1

    event = state.execution_trace[0]

    assert event["stage"] == "generation"
    assert event["attempt"] == 0
    assert event["status"] == "success"
    assert event["message"] == (
        "SQL generated successfully."
    )

def test_agent_state_can_store_business_knowledge():

    document = BusinessKnowledgeDocument(
        document_id="metric.revenue",
        title="Revenue",
        content="Revenue definition",
        source="test",
        keywords=["revenue"],
    )

    result = BusinessKnowledgeResult(
        query="Show revenue",
        matches=[
            BusinessKnowledgeMatch(
                document=document,
                score=1.0,
                matched_keywords=["revenue"],
            )
        ],
    )

    state = AgentState(
        question="Show revenue",
        business_knowledge=result,
    )

    assert state.business_knowledge is result
    assert (
        state.business_knowledge.matches[0]
        .document.document_id
        == "metric.revenue"
    )
