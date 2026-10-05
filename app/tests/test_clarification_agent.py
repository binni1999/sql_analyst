from agents.clarification_agent import ClarificationAgent
from models.state import AgentState


def test_clarification_agent_detects_ambiguous_best():

    agent = ClarificationAgent()

    state = AgentState(
        question="Show me the best products"
    )

    result = agent.run(state)

    assert result.needs_clarification is True
    assert result.question is not None
    assert len(result.options) > 0


def test_clarification_agent_allows_explicit_metric():

    agent = ClarificationAgent()

    state = AgentState(
        question="Show the best products by revenue"
    )

    result = agent.run(state)

    assert result.needs_clarification is False


def test_clarification_agent_allows_top_products_by_revenue():

    agent = ClarificationAgent()

    state = AgentState(
        question="Show top 5 products by revenue"
    )

    result = agent.run(state)

    assert result.needs_clarification is False


def test_clarification_agent_handles_normal_query():

    agent = ClarificationAgent()

    state = AgentState(
        question="Find customers from Delhi"
    )

    result = agent.run(state)

    assert result.needs_clarification is False
    

def test_clarification_agent_adds_trace_when_clarification_is_required():

    agent = ClarificationAgent()

    state = AgentState(
        question="Show me the best products"
    )

    result = agent.run(state)

    assert result.needs_clarification is True
    assert len(state.execution_trace) == 2
    assert state.execution_trace[0]["stage"] == "clarification"
    assert state.execution_trace[0]["status"] == "started"
    assert state.execution_trace[1]["stage"] == "clarification"
    assert state.execution_trace[1]["status"] == "required"
    assert state.execution_trace[1]["metadata"]["ambiguous_term"] == "best"


def test_clarification_agent_adds_success_trace_for_explicit_metric():

    agent = ClarificationAgent()

    state = AgentState(
        question="Show the best products by revenue"
    )

    result = agent.run(state)

    assert result.needs_clarification is False
    assert len(state.execution_trace) == 2
    assert state.execution_trace[-1]["stage"] == "clarification"
    assert state.execution_trace[-1]["status"] == "success"
    assert state.execution_trace[-1]["metadata"]["ambiguous_term"] == "best"
