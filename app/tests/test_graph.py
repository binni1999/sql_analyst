from models.state import AgentStep
from agents.clarification_agent import ClarificationAgent
from agents.intent_agent import IntentAgent

from graph.routing import (
    route_after_analytics,
    route_after_clarification,
    route_after_intent,
    route_after_metadata,
    route_after_sql,
    route_after_business_knowledge,
)

from graph.state import create_initial_graph_state
from graph.workflow import DataAnalystGraph

from models.agent import (
    AnalyticsResult,
    MetadataResult,
    SQLResult,
)

from models.clarification import ClarificationResult
from models.intent import QuestionIntent


# ============================================================
# MOCK METADATA AGENT
# ============================================================

class MockMetadataAgent:

    def run(self, state):

        state.metadata = MetadataResult(
            schemas=[],
            schema_text="TEST SCHEMA",
            metadata="TEST METADATA",
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
            errors=[],
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
            },
        )

        return state


# ============================================================
# MOCK ANSWER GENERATOR
# ============================================================

class MockAnswerGenerator:

    def generate(
        self,
        question,
        analyzed_result,
    ):
        assert question == "Show revenue"

        assert analyzed_result == {
            "row_count": 1
        }

        return "Test answer"


# ============================================================
# HELPER
# ============================================================

def create_test_graph():

    return DataAnalystGraph(
        intent_agent=IntentAgent(),
        clarification_agent=ClarificationAgent(),
        metadata_agent=MockMetadataAgent(),
        sql_agent=MockSQLAgent(),
        analytics_agent=MockAnalyticsAgent(),
        answer_generator=MockAnswerGenerator(),
    )


# ============================================================
# TEST 1
# Initial Graph State
# ============================================================

def test_initial_graph_state():

    state = create_initial_graph_state(
        question="Show total revenue"
    )

    assert "agent_state" in state

    assert (
        state["agent_state"].question
        == "Show total revenue"
    )

    assert (
        state["agent_state"].current_step.value
        == "initialized"
    )


# ============================================================
# TEST 2
# Intent Routing - Supported
# ============================================================

def test_route_after_intent_supported():

    state = create_initial_graph_state(
        question="Show total revenue"
    )

    state["agent_state"].intent = (
        QuestionIntent.DATA_QUERY
    )

    assert route_after_intent(state) == (
        "clarification"
    )


# ============================================================
# TEST 3
# Intent Routing - Unknown
# ============================================================

def test_route_after_intent_unknown():

    state = create_initial_graph_state(
        question="Hello"
    )

    state["agent_state"].intent = (
        QuestionIntent.UNKNOWN
    )

    assert route_after_intent(state) == "end"


# ============================================================
# TEST 4
# Clarification Routing - Clear
# ============================================================

def test_route_after_clarification_clear():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].clarification = (
        ClarificationResult(
            needs_clarification=False,
            question=None,
            reason=None,
            options=[],
        )
    )

    assert route_after_clarification(state) == (
        "metadata"
    )


# ============================================================
# TEST 5
# Clarification Routing - Required
# ============================================================

def test_route_after_clarification_required():

    state = create_initial_graph_state(
        question="Show sales"
    )

    state["agent_state"].clarification = (
        ClarificationResult(
            needs_clarification=True,
            question="Which metric do you mean?",
            reason="Metric is ambiguous.",
            options=[
                "Revenue",
                "Quantity",
            ],
        )
    )

    assert route_after_clarification(state) == (
        "end"
    )


# ============================================================
# TEST 7
# Metadata Routing - Success
# ============================================================

def test_route_after_metadata_success():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].metadata = MetadataResult(
        schemas=[],
        schema_text="TEST SCHEMA",
        metadata="TEST METADATA",
    )

    assert route_after_metadata(state) == "business_knowledge"


# ============================================================
# TEST 8
# Metadata Routing - Failure
# ============================================================

def test_route_after_metadata_failure():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    assert route_after_metadata(state) == "end"


# ============================================================
# TEST 9
# SQL Routing - Success
# ============================================================

def test_route_after_sql_success():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].sql = SQLResult(
        success=True,
        sql="SELECT 1",
        attempts=1,
        errors=[],
    )

    assert route_after_sql(state) == "analytics"


# ============================================================
# TEST 10
# SQL Routing - Failure
# ============================================================

def test_route_after_sql_failure():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].sql = SQLResult(
        success=False,
        sql="SELECT invalid",
        attempts=3,
        errors=["SQL validation failed"],
    )

    assert route_after_sql(state) == "end"


# ============================================================
# TEST 11
# Analytics Routing - Success
# ============================================================

def test_route_after_analytics_success():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].analytics = AnalyticsResult(
        success=True,
        analysis={"row_count": 1},
    )

    assert route_after_analytics(state) == "answer"


# ============================================================
# TEST 12
# Analytics Routing - Failure
# ============================================================

def test_route_after_analytics_failure():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].analytics = AnalyticsResult(
        success=False,
        analysis={},
        error="Analytics failed",
    )

    assert route_after_analytics(state) == "end"


# ============================================================
# TEST 6
# REAL LANGGRAPH WORKFLOW
# ============================================================

def test_langgraph_full_workflow():

    graph = create_test_graph()

    result = graph.run(
        question="Show revenue"
    )

    # --------------------------------------------------------
    # Final state
    # --------------------------------------------------------

    assert result is not None

    # --------------------------------------------------------
    # Intent
    # --------------------------------------------------------

    assert result.intent == (
        QuestionIntent.DATA_QUERY
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    assert result.metadata is not None

    assert result.metadata.schema_text == (
        "TEST SCHEMA"
    )

    assert result.metadata.metadata == (
        "TEST METADATA"
    )

    # --------------------------------------------------------
    # SQL
    # --------------------------------------------------------

    assert result.sql is not None

    assert result.sql.success is True

    assert result.sql.sql == "SELECT 1"

    # --------------------------------------------------------
    # Analytics
    # --------------------------------------------------------

    assert result.analytics is not None

    assert result.analytics.success is True

    assert result.analytics.analysis == {
        "row_count": 1
    }

    # --------------------------------------------------------
    # Answer
    # --------------------------------------------------------

    assert result.answer == "Test answer"

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    assert result.success is True
    assert result.current_step == AgentStep.COMPLETED

def test_route_after_business_knowledge_success():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    # pyrefly: ignore [unknown-name]
    assert route_after_business_knowledge(state) == "sql"
