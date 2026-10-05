from typing import Any

from pydantic import BaseModel, Field


class BusinessKnowledgeDocument(BaseModel):
    """
    A business-facing knowledge unit used by the RAG layer.
    """

    document_id: str
    title: str
    content: str
    source: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    keywords: list[str] = Field(
        default_factory=list
    )


class BusinessKnowledgeMatch(BaseModel):
    """
    A retrieved business-knowledge document
    together with its relevance score.
    """

    document: BusinessKnowledgeDocument

    score: float

    matched_keywords: list[str] = Field(
        default_factory=list
    )


class BusinessKnowledgeResult(BaseModel):
    """
    Result returned by the business knowledge retriever.
    """

    query: str

    matches: list[BusinessKnowledgeMatch] = Field(
        default_factory=list
    )