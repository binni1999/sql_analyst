import pytest

# pyrefly: ignore [missing-import]
from agents.business_knowledge_agent import (
    BusinessKnowledgeAgent,
)
from knowledge.business_documents import (
    BUSINESS_KNOWLEDGE_DOCUMENTS,
)
from models.business_knowledge import (
    BusinessKnowledgeResult,
)
from models.state import AgentState
from services.business_knowledge_retriever import (
    BusinessKnowledgeRetriever,
)


def test_business_knowledge_agent_calls_retriever():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=2,
    )

    state = AgentState(
        question="Show total revenue"
    )

    result = agent.run(state)

    assert isinstance(
        result,
        BusinessKnowledgeResult,
    )

    assert result.query == (
        "Show total revenue"
    )


def test_business_knowledge_agent_returns_revenue_match():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    state = AgentState(
        question="What is the revenue?"
    )

    result = agent.run(state)

    document_ids = [
        match.document.document_id
        for match in result.matches
    ]

    assert "metric.revenue" in document_ids


def test_business_knowledge_agent_adds_trace_events():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    state = AgentState(
        question="Show revenue"
    )

    agent.run(state)

    business_events = [
        event
        for event in state.execution_trace
        if event["stage"] == "business_knowledge"
    ]

    assert len(business_events) == 2

    assert business_events[0]["status"] == "started"

    assert business_events[1]["status"] == "success"


def test_business_knowledge_agent_trace_contains_matches():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    state = AgentState(
        question="Show revenue"
    )

    agent.run(state)

    success_event = next(
        event
        for event in state.execution_trace
        if (
            event["stage"]
            == "business_knowledge"
            and event["status"]
            == "success"
        )
    )

    assert (
        success_event["metadata"]["match_count"]
        >= 1
    )

    assert (
        "metric.revenue"
        in success_event["metadata"][
            "matched_document_ids"
        ]
    )


def test_business_knowledge_agent_does_not_modify_question():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    agent = BusinessKnowledgeAgent(
        retriever=retriever,
        top_k=3,
    )

    state = AgentState(
        question="Show total revenue"
    )

    original_question = state.question

    agent.run(state)

    assert state.question == original_question


def test_business_knowledge_agent_records_failure():

    class FailingRetriever:

        def retrieve(
            self,
            query: str,
            top_k: int,
        ):
            raise RuntimeError(
                "Retriever failed"
            )

    agent = BusinessKnowledgeAgent(
        retriever=FailingRetriever(),
        top_k=3,
    )

    state = AgentState(
        question="Show revenue"
    )

    with pytest.raises(RuntimeError):
        agent.run(state)

    business_events = [
        event
        for event in state.execution_trace
        if event["stage"]
        == "business_knowledge"
    ]

    assert len(business_events) == 2

    assert (
        business_events[0]["status"]
        == "started"
    )

    assert (
        business_events[1]["status"]
        == "failed"
    )

    assert (
        business_events[1]["error_type"]
        == "business_knowledge"
    )

    assert (
        business_events[1]["metadata"][
            "exception_type"
        ]
        == "RuntimeError"
    )