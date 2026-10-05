from models.clarification import ClarificationResult
from models.execution_trace import ExecutionTraceEvent
from models.state import AgentState


class ClarificationAgent:

    AMBIGUOUS_TERMS = {
        "best",
        "good",
        "popular",
        "successful",
        "worst"
    }

    METRIC_KEYWORDS = {
        "revenue",
        "sales",
        "quantity",
        "units",
        "rating",
        "reviews",
        "orders",
        "customers"
    }

    def _add_trace_event(
        self,
        state: AgentState,
        *,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ):
        event = ExecutionTraceEvent(
            stage="clarification",
            status=status,
            attempt=0,
            message=message,
            metadata={
                "component": self.__class__.__name__,
                **(metadata or {}),
            },
        )
        state.execution_trace.append(
        event.model_dump(exclude_none=True)
    )

    def run(
        self,
        state: AgentState
    ) -> ClarificationResult:

        self._add_trace_event(
            state,
            status="started",
            message="Clarification analysis started.",
        )

        question = state.question.lower().strip()

        # ---------------------------------------------------------
        # Check whether the question contains an ambiguous term
        # ---------------------------------------------------------

        ambiguous_terms = [
            term
            for term in self.AMBIGUOUS_TERMS
            if term in question
        ]

        if not ambiguous_terms:
            self._add_trace_event(
                state,
                status="success",
                message="No ambiguous term detected; clarification is not required.",
            )

            return ClarificationResult(
                needs_clarification=False
            )

        # ---------------------------------------------------------
        # Check whether the user already specified a metric
        # ---------------------------------------------------------

        has_metric = any(
            metric in question
            for metric in self.METRIC_KEYWORDS
        )

        if has_metric:
            self._add_trace_event(
                state,
                status="success",
                message="An explicit metric is present; clarification is not required.",
                metadata={"ambiguous_term": ambiguous_terms[0]},
            )

            return ClarificationResult(
                needs_clarification=False
            )

        # ---------------------------------------------------------
        # Build clarification question
        # ---------------------------------------------------------

        term = ambiguous_terms[0]

        self._add_trace_event(
            state,
            status="required",
            message="Clarification is required because an ambiguous term has no metric.",
            metadata={"ambiguous_term": term},
        )

        return ClarificationResult(
            needs_clarification=True,
            question=(
                f"What do you mean by '{term}'? "
                "Please specify the metric you want to use."
            ),
            reason=(
                "The question contains an ambiguous ranking "
                "or comparison term without specifying a metric."
            ),
            options=[
                "Highest revenue",
                "Most units sold",
                "Highest customer rating"
            ]
        )
