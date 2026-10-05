import re

from models.business_knowledge import (
    BusinessKnowledgeDocument,
    BusinessKnowledgeMatch,
    BusinessKnowledgeResult,
)


class BusinessKnowledgeRetriever:
    """
    Deterministic retrieval implementation for business knowledge.

    This is intentionally NOT an embedding/vector implementation yet.

    It establishes the retrieval contract that the
    BusinessKnowledgeAgent will consume in the next milestone.
    """

    def __init__(
        self,
        documents: list[BusinessKnowledgeDocument],
    ):
        self.documents = list(documents)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        """
        Convert text into normalized alphanumeric tokens.
        """

        return set(
            re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> BusinessKnowledgeResult:
        """
        Retrieve the most relevant business knowledge documents.

        Parameters
        ----------
        query:
            User/business question.

        top_k:
            Maximum number of documents to return.
        """

        if top_k <= 0:
            return BusinessKnowledgeResult(
                query=query
            )

        query_tokens = self._tokens(query)

        matches: list[
            BusinessKnowledgeMatch
        ] = []

        for document in self.documents:

            keyword_tokens: set[str] = set()

            for keyword in document.keywords:
                keyword_tokens.update(
                    self._tokens(keyword)
                )

            matched_keywords = [
                keyword
                for keyword in document.keywords
                if self._tokens(keyword)
                & query_tokens
            ]

            overlap = (
                query_tokens
                & keyword_tokens
            )

            score = (
                len(overlap)
                / len(query_tokens)
                if query_tokens
                else 0.0
            )

            if score > 0:

                matches.append(
                    BusinessKnowledgeMatch(
                        document=document,
                        score=score,
                        matched_keywords=(
                            matched_keywords
                        ),
                    )
                )

        matches.sort(
            key=lambda match: (
                -match.score,
                match.document.document_id,
            )
        )

        return BusinessKnowledgeResult(
            query=query,
            matches=matches[:top_k],
        )