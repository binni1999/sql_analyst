from models.execution_trace import ExecutionTraceEvent
from models.intent import QuestionIntent
from models.state import AgentState


class IntentAgent:

    def _add_trace_event(
        self,
        state: AgentState,
        *,
        status: str,
        message: str,
    ):
        event = ExecutionTraceEvent(
            stage="intent",
            status=status,
            attempt=0,
            message=message,
            metadata={
                "component": self.__class__.__name__,
            },
        )
        state.execution_trace.append(
            event.model_dump(exclude_none=True)
        )

    def run(self, state: AgentState):

        self._add_trace_event(
            state,
            status="started",
            message="Intent classification started.",
        )

        question = state.question.lower().strip()

        if not question:

            state.intent = QuestionIntent.UNKNOWN

            self._add_trace_event(
                state,
                status="success",
                message="Question classified as UNKNOWN because it is empty.",
            )

            return state

        data_keywords = [
            "show",
            "find",
            "list",
            "get",
            "calculate",
            "count",
            "average",
            "sum",
            "total",
            "revenue",
            "sales",
            "product",
            "customer",
            "order",
            "orders",
            "payment",
            "review"
        ]

        if any(
            keyword in question
            for keyword in data_keywords
        ):

            state.intent = QuestionIntent.DATA_QUERY

            self._add_trace_event(
                state,
                status="success",
                message="Question classified as DATA_QUERY.",
            )

        else:

            state.intent = QuestionIntent.UNKNOWN

            self._add_trace_event(
                state,
                status="success",
                message="Question classified as UNKNOWN.",
            )

        return state
