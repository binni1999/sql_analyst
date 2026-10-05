from knowledge.business_documents import (
    BUSINESS_KNOWLEDGE_DOCUMENTS,
)

from models.business_knowledge import (
    BusinessKnowledgeDocument,
)

from services.business_knowledge_retriever import (
    BusinessKnowledgeRetriever,
)


def test_business_knowledge_documents_are_structured():

    assert BUSINESS_KNOWLEDGE_DOCUMENTS

    assert all(
        isinstance(
            document,
            BusinessKnowledgeDocument,
        )
        for document in BUSINESS_KNOWLEDGE_DOCUMENTS
    )


def test_retriever_returns_revenue_for_sales_query():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    result = retriever.retrieve(
        "What were our total sales revenue?",
        top_k=2,
    )

    assert result.matches

    assert (
        result.matches[0]
        .document
        .document_id
        == "metric.revenue"
    )

    assert (
        "sales"
        in result.matches[0].matched_keywords
    )


def test_retriever_returns_quantity_for_units_query():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    result = retriever.retrieve(
        "How many units were sold?",
        top_k=2,
    )

    assert result.matches

    assert (
        result.matches[0]
        .document
        .document_id
        == "metric.quantity"
    )


def test_retriever_returns_no_match_for_unrelated_query():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    result = retriever.retrieve(
        "Which customers live in Delhi?",
        top_k=2,
    )

    assert result.matches == []


def test_retriever_respects_top_k_and_zero():

    retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    result = retriever.retrieve(
        "sales units",
        top_k=1,
    )

    assert len(result.matches) == 1

    result = retriever.retrieve(
        "sales units",
        top_k=0,
    )

    assert result.matches == []