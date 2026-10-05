from typing import TypedDict

from models.analytical_context import AnalyticalContext
from models.state import AgentState


class GraphState(TypedDict):
    """
    LangGraph state wrapper.

    The actual business/application state remains the existing
    AgentState model. LangGraph is responsible for orchestration,
    while AgentState continues to hold the workflow data.
    """

    agent_state: AgentState


def create_initial_graph_state(
    question: str,
    analytical_context: AnalyticalContext | None = None,
) -> GraphState:
    """
    Create the initial state used by the LangGraph workflow.
    """

    return {
        "agent_state": AgentState(
            question=question,
            analytical_context=analytical_context,
        )
    }