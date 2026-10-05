from agents.intent_agent import IntentAgent
from models.intent import QuestionIntent
from models.state import AgentState


def test_intent_agent_detects_data_query():

    agent = IntentAgent()

    state = AgentState(
        question="Show the top 5 products by revenue"
    )

    result = agent.run(state)

    assert result.intent == QuestionIntent.DATA_QUERY


def test_intent_agent_detects_customer_query():

    agent = IntentAgent()

    state = AgentState(
        question="Find all customers from Delhi"
    )

    result = agent.run(state)

    assert result.intent == QuestionIntent.DATA_QUERY


def test_intent_agent_returns_unknown():

    agent = IntentAgent()

    state = AgentState(
        question="Hello"
    )

    result = agent.run(state)

    assert result.intent == QuestionIntent.UNKNOWN


def test_intent_agent_handles_empty_question():

    agent = IntentAgent()

    state = AgentState(
        question=""
    )

    result = agent.run(state)

    assert result.intent == QuestionIntent.UNKNOWN

def test_intent_agent_adds_execution_trace():

    agent = IntentAgent()

    state = AgentState(
        question="Show the top 5 products by revenue"
    )

    result = agent.run(state)

    assert len(result.execution_trace) == 2
    assert result.execution_trace[0]["stage"] == "intent"
    assert result.execution_trace[0]["status"] == "started"
    assert result.execution_trace[1]["stage"] == "intent"
    assert result.execution_trace[1]["status"] == "success"
