from agents.intent_agent import IntentAgent
from agents.clarification_agent import ClarificationAgent
from graph.nodes import human_approval_node, risk_check_node
from graph.routing import route_after_human_approval, route_after_risk_check
from graph.state import create_initial_graph_state
from models.agent import SQLResult
from models.human_approval import HumanApprovalStatus
from models.state import AgentStep


def make_state(sql: str):
    state = create_initial_graph_state("Show data")
    state["agent_state"].sql = SQLResult(
        success=True,
        sql=sql,
        attempts=1,
        errors=[],
    )
    return state


def test_risk_check_pauses_risky_query():
    state = make_state("SELECT COUNT(*) FROM orders")

    result = risk_check_node(state)
    agent_state = result["agent_state"]

    assert agent_state.human_approval_required is True
    assert agent_state.human_approval_status == HumanApprovalStatus.PENDING
    assert agent_state.current_step == AgentStep.HUMAN_APPROVAL
    assert route_after_risk_check(result) == "end"


def test_risk_check_allows_safe_query():
    state = make_state("SELECT 1")

    result = risk_check_node(state)
    agent_state = result["agent_state"]

    assert agent_state.human_approval_required is False
    assert agent_state.human_approval_status == HumanApprovalStatus.NOT_REQUIRED
    assert route_after_risk_check(result) == "analytics"


def test_human_approval_approve_routes_to_analytics():
    state = make_state("SELECT COUNT(*) FROM orders")
    risk_result = risk_check_node(state)

    result = human_approval_node(risk_result, True)
    agent_state = result["agent_state"]

    assert agent_state.human_approval_status == HumanApprovalStatus.APPROVED
    assert agent_state.human_approval_required is False
    assert route_after_human_approval(result) == "analytics"


def test_human_approval_reject_terminates():
    state = make_state("SELECT COUNT(*) FROM orders")
    risk_result = risk_check_node(state)

    result = human_approval_node(risk_result, False)
    agent_state = result["agent_state"]

    assert agent_state.human_approval_status == HumanApprovalStatus.REJECTED
    assert agent_state.success is False
    assert agent_state.current_step == AgentStep.FAILED
    assert route_after_human_approval(result) == "end"
