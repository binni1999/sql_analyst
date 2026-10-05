from models.execution_trace import ExecutionTraceEvent
from models.state import AgentState


class BusinessKnowledgeAgent:
    """
    Agent responsible for retrieving relevant business knowledge.

    The agent intentionally does not:
    - generate SQL
    - modify SQL
    - modify analytical context
    - orchestrate other agents

    Its only responsibility is to retrieve business knowledge
    and return a BusinessKnowledgeResult.
    """

    def __init__(
        self,
        retriever,
        top_k: int = 3,
    ):
        self.retriever = retriever
        self.top_k = top_k

    def _add_trace_event(
        self,
        state: AgentState,
        *,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
        error_type: str | None = None,
    ) -> None:
        """
        Add a business-knowledge execution event to AgentState.
        """

        event = ExecutionTraceEvent(
            stage="business_knowledge",
            status=status,
            attempt=0,
            message=message,
            error_type=error_type,
            metadata=metadata or {},
        )

        state.execution_trace.append(
            event.model_dump(
                exclude_none=True
            )
        )

    def run(
        self,
        state: AgentState,
    ):
        """
        Retrieve business knowledge for the current question.

        Parameters
        ----------
        state:
            Current AgentState.

        Returns
        -------
        BusinessKnowledgeResult
            Retrieved business knowledge.
        """

        self._add_trace_event(
            state,
            status="started",
            message=(
                "Business knowledge retrieval started."
            ),
            metadata={
                "component": self.__class__.__name__,
                "top_k": self.top_k,
            },
        )

        try:
            result = self.retriever.retrieve(
                query=state.question,
                top_k=self.top_k,
            )

            self._add_trace_event(
                state,
                status="success",
                message=(
                    "Business knowledge retrieval completed."
                ),
                metadata={
                    "match_count": len(
                        result.matches
                    ),
                    "matched_document_ids": [
                        match.document.document_id
                        for match in result.matches
                    ],
                },
            )

            return result

        except Exception as exc:

            self._add_trace_event(
                state,
                status="failed",
                message=(
                    "Business knowledge retrieval failed."
                ),
                error_type="business_knowledge",
                metadata={
                    "exception_type": type(
                        exc
                    ).__name__,
                },
            )

            raise