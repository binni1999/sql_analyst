from models.state import AgentStep
from models.intent import QuestionIntent


# Intents that are currently supported by the analytical workflow.
# Keeping this explicit prevents a newly introduced intent from
# accidentally entering the SQL pipeline without a routing decision.
SUPPORTED_INTENTS = {
    QuestionIntent.DATA_QUERY,
}


def route_after_intent(state) -> str:
    """Route supported analytical questions to clarification.

    Unknown or unsupported intents terminate the graph.
    """
    agent_state = state["agent_state"]

    if agent_state.intent not in SUPPORTED_INTENTS:
        return "end"

    return "clarification"


def route_after_clarification(state) -> str:
    """Stop for user clarification when the clarification agent requires it."""
    agent_state = state["agent_state"]
    clarification = agent_state.clarification

    if clarification and clarification.needs_clarification:
        return "end"

    return "metadata"


def route_after_metadata(state) -> str:
    agent_state = state["agent_state"]
    if not agent_state.metadata:
        return "end"
    return "business_knowledge"


def route_after_business_knowledge(state) -> str:
    agent_state = state["agent_state"]
    if (
        agent_state.error
        and agent_state.current_step == AgentStep.FAILED
    ):
        return "end"
    return "sql"


    if not agent_state.metadata:
        return "end"

    return "sql"


def route_after_sql(state) -> str:
    """Continue to analytics only after successful SQL execution/validation."""
    agent_state = state["agent_state"]

    if not agent_state.sql or not agent_state.sql.success:
        return "end"

    return "analytics"


def route_after_analytics(state) -> str:
    """Continue to answer generation only after successful analytics."""
    agent_state = state["agent_state"]

    if not agent_state.analytics or not agent_state.analytics.success:
        return "end"

    return "answer"


def route_after_risk_check(state) -> str:
    """Continue after risk review; pending/rejected approvals terminate."""
    from models.human_approval import HumanApprovalStatus

    agent_state = state["agent_state"]

    if agent_state.human_approval_status in {
        HumanApprovalStatus.PENDING,
        HumanApprovalStatus.REJECTED,
    }:
        return "end"

    return "analytics"


def route_after_human_approval(state) -> str:
    """Continue only after an explicit approval decision."""
    agent_state = state["agent_state"]
    if agent_state.human_approval_status.value == "approved":
        return "analytics"
    return "end"
