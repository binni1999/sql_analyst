from agents.clarification_agent import ClarificationAgent
from agents.coordinator import CoordinatorAgent

from models.agent import (
    MetadataResult,
    SQLResult,
    AnalyticsResult
)

from models.state import AgentState, AgentStep
from agents.intent_agent import IntentAgent
from unittest.mock import Mock
import pytest

from models.clarification import ClarificationResult

# ============================================================
# MOCK METADATA AGENT
# ============================================================
class MockMetadataAgent:

    def run(self, state):

        state.metadata = MetadataResult(
            schemas=[],
            schema_text="TEST SCHEMA",
            metadata="TEST METADATA"
        )

        return state


# ============================================================
# MOCK SQL AGENT
# ============================================================

class MockSQLAgent:

    def run(self, state):

        assert state.question == "Show revenue"

        assert state.metadata is not None

        assert state.metadata.schema_text == (
            "TEST SCHEMA"
        )

        assert state.metadata.metadata == (
            "TEST METADATA"
        )

        state.sql = SQLResult(
            success=True,
            sql="SELECT 1",
            attempts=1,
            errors=[]
        )

        return state

# ============================================================
# MOCK ANALYTICS AGENT
# ============================================================

class MockAnalyticsAgent:

    def run(self, state):

        assert state.question == "Show revenue"

        assert state.sql is not None

        assert state.sql.success is True

        assert state.sql.sql == "SELECT 1"

        state.analytics = AnalyticsResult(
            success=True,
            analysis={
                "row_count": 1
            }
        )

        return state


# ============================================================
# FAILING SQL AGENT
# ============================================================

class FailingSQLAgent:

    def run(self, state):

        state.sql = SQLResult(
            success=False,
            sql=None,
            attempts=4,
            errors=[
                "Unable to generate valid SQL"
            ]
        )

        return state


# ============================================================
# FAILING ANALYTICS AGENT
# ============================================================

class FailingAnalyticsAgent:

    def run(self, state):

        state.analytics = AnalyticsResult(
            success=False,
            error="Database execution failed"
        )

        return state

class MockAnswerGenerator:

    def generate(
        self,
        question,
        analyzed_result
    ):
        return "Test answer"
# ============================================================
# TEST 1
# Metadata Agent → SQL Agent → Analytics Agent
# ============================================================

def test_coordinator_metadata_to_sql():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Show revenue"
    )
    assert result.current_step == AgentStep.COMPLETED

    # Verify question
    assert result.question == "Show revenue"

    # Verify MetadataResult
    assert result.metadata.schema_text == (
        "TEST SCHEMA"
    )

    assert result.metadata.metadata == (
        "TEST METADATA"
    )

    # Verify SQLResult
    assert result.sql.success is True

    assert result.sql.sql == "SELECT 1"

    assert result.sql.attempts == 1

    # Verify AnalyticsResult
    assert result.analytics.success is True

    assert result.analytics.analysis["row_count"] == 1

    # Verify overall state
    assert result.answer == "Test answer"
    assert result.success is True

    assert result.error is None
   
   
    assert result.current_step == AgentStep.COMPLETED


# ============================================================
# TEST 2
# Coordinator stops when SQL Agent fails
# ============================================================

def test_coordinator_stops_when_sql_agent_fails():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=FailingSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Show revenue"
    )
    assert result.current_step == AgentStep.FAILED

    # Overall pipeline should fail
    assert result.success is False

    # SQL Agent should have failed
    assert result.sql.success is False

    assert result.sql.sql is None

    # Analytics Agent should NOT be called
    assert result.analytics is None

    # Error should come from SQL Agent
    assert result.error == [
        "Unable to generate valid SQL"
    ]


# ============================================================
# TEST 3
# Coordinator handles Analytics Agent failure
# ============================================================

def test_coordinator_handles_analytics_failure():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=FailingAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Show revenue"
    )
    assert result.current_step == AgentStep.FAILED

    # Overall pipeline should fail
    assert result.success is False

    # SQL Agent should have succeeded
    assert result.sql.success is True

    assert result.sql.sql == "SELECT 1"

    # Analytics Agent should have failed
    assert result.analytics.success is False

    assert result.analytics.error == (
        "Database execution failed"
    )

    # Coordinator should propagate analytics error
    assert result.error == (
        "Database execution failed"
    )

def test_coordinator_records_analytics_duration_on_failure():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=FailingAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Show revenue"
    )

    assert result.success is False

    analytics_events = [
        event
        for event in result.execution_trace
        if event["stage"] == "analytics"
        and event["status"] == "failed"
    ]

    assert len(analytics_events) == 1

    assert "duration_ms" in analytics_events[0]

    assert analytics_events[0]["duration_ms"] >= 0

def test_coordinator_records_sql_duration_on_failure():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=FailingSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Show revenue"
    )

    assert result.success is False

    sql_events = [
        event
        for event in result.execution_trace
        if event["stage"] == "sql_agent"
        and event["status"] == "failed"
    ]

    assert len(sql_events) == 1

    assert "duration_ms" in sql_events[0]

    assert sql_events[0]["duration_ms"] >= 0

# ============================================================
# TEST 4
# Centralized state update
# ============================================================



def test_coordinator_stops_for_unknown_intent():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    result = coordinator.run(
        "Hello"
    )

    assert result.success is False
    assert result.current_step == AgentStep.FAILED
    assert result.error == "Unable to determine question intent."


def test_coordinator_stops_for_clarification():

    clarification_agent = Mock()

    clarification_agent.run.return_value = (
        ClarificationResult(
            needs_clarification=True,
            question="What do you mean by 'best'?",
            reason="Metric not specified.",
            options=[
                "Highest revenue",
                "Most units sold",
                "Highest customer rating"
            ]
        )
    )

    metadata_agent = Mock()
    sql_agent = Mock()
    analytics_agent = Mock()
    answer_generator = Mock()

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        clarification_agent=clarification_agent,
        metadata_agent=metadata_agent,
        sql_agent=sql_agent,
        analytics_agent=analytics_agent,
        answer_generator=answer_generator
    )

    state = coordinator.run(
        "Show me the best products"
    )

    assert state.success is True

    assert state.clarification is not None

    assert (
        state.clarification.needs_clarification
        is True
    )

    assert state.sql is None

    metadata_agent.run.assert_not_called()
    sql_agent.run.assert_not_called()
    analytics_agent.run.assert_not_called()
    answer_generator.generate.assert_not_called()

def test_coordinator_records_stage_durations():
    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    state = coordinator.run(
        "Show revenue"
    )

    assert state.success is True

    sql_events = [
        event
        for event in state.execution_trace
        if event["stage"] == "sql_agent"
        and event["status"] == "success"
    ]

    analytics_events = [
        event
        for event in state.execution_trace
        if event["stage"] == "analytics"
        and event["status"] == "success"
    ]

    answer_events = [
        event
        for event in state.execution_trace
        if event["stage"] == "answer_generation"
        and event["status"] == "success"
    ]

    assert len(sql_events) == 1
    assert len(analytics_events) == 1
    assert len(answer_events) == 1

    assert sql_events[0]["duration_ms"] >= 0
    assert analytics_events[0]["duration_ms"] >= 0
    assert answer_events[0]["duration_ms"] >= 0
 

# ============================================================
# TEST 5
# State transition validation
# ============================================================


def test_valid_state_transition():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    state = AgentState(
        question="Show revenue"
    )

    coordinator._transition(
        state,
        AgentStep.CLARIFICATION,
    )

    assert state.current_step == AgentStep.CLARIFICATION


def test_invalid_state_transition_is_rejected():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    state = AgentState(
        question="Show revenue"
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid state transition"
    ):
        coordinator._transition(
            state,
            AgentStep.SQL,
        )


def test_failed_state_cannot_transition():

    coordinator = CoordinatorAgent(
        intent_agent=IntentAgent(),
        metadata_agent=MockMetadataAgent(),
        clarification_agent=ClarificationAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator()
    )

    state = AgentState(
        question="Show revenue"
    )

    state.mark_failure("Test failure")

    with pytest.raises(
        RuntimeError,
        match="Cannot transition from FAILED"
    ):
        coordinator._transition(
            state,
            AgentStep.CLARIFICATION,
        )