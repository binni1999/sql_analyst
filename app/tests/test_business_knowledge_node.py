from agents.business_knowledge_agent import BusinessKnowledgeAgent
from graph.nodes import business_knowledge_node
from knowledge.business_documents import BUSINESS_KNOWLEDGE_DOCUMENTS
from models.state import AgentState
from services.business_knowledge_retriever import BusinessKnowledgeRetriever


def test_business_knowledge_node_attaches_result_to_state():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    state = {
        "agent_state": AgentState(
            question="What is the revenue?"
        )
    }

    result = business_knowledge_node(
        state,
        agent,
    )

    agent_state = result["agent_state"]

    assert agent_state.business_knowledge is not None

    document_ids = [
        match.document.document_id
        for match in agent_state.business_knowledge.matches
    ]

    assert "metric.revenue" in document_ids


def test_business_knowledge_node_preserves_question():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    agent_state = AgentState(
        question="Show total revenue"
    )

    state = {
        "agent_state": agent_state
    }

    business_knowledge_node(
        state,
        agent,
    )

    assert agent_state.question == "Show total revenue"


def test_business_knowledge_node_without_agent_is_backward_compatible():

    agent_state = AgentState(
        question="Show revenue"
    )

    state = {
        "agent_state": agent_state
    }

    result = business_knowledge_node(
        state,
        None,
    )

    assert result["agent_state"] is agent_state
    assert agent_state.business_knowledge is None
