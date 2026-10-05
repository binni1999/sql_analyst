import time


from models.intent import QuestionIntent
from models.state import AgentState, AgentStep
from models.analytical_context import AnalyticalContext
from models.execution_trace import ExecutionTraceEvent


class CoordinatorAgent:

    def __init__(
        self,
        intent_agent,
        clarification_agent,
        metadata_agent,
        sql_agent,
        analytics_agent,
        answer_generator
    ):
        self.intent_agent = intent_agent
        self.clarification_agent = clarification_agent
        self.metadata_agent = metadata_agent
        self.sql_agent = sql_agent
        self.analytics_agent = analytics_agent
        self.answer_generator = answer_generator

    # ============================================================
    # STATE TRANSITIONS
    # ============================================================

    ALLOWED_TRANSITIONS = {
        AgentStep.INITIALIZED: {
            AgentStep.CLARIFICATION,
        },
        AgentStep.CLARIFICATION: {
            AgentStep.METADATA,
        },
        AgentStep.METADATA: {
            AgentStep.SQL,
        },
        AgentStep.SQL: {
            AgentStep.ANALYTICS,
        },
        AgentStep.ANALYTICS: {
            AgentStep.ANSWER,
        },
        AgentStep.ANSWER: {
            AgentStep.COMPLETED,
        },
    }

    def _transition(
        self,
        state: AgentState,
        next_step: AgentStep,
    ) -> None:
        """
        Enforce valid Coordinator state transitions.

        FAILED is a terminal state and can be reached through
        state.mark_failure().

        Raises:
            RuntimeError: If an invalid workflow transition is attempted.
        """

        current_step = state.current_step

        if current_step == AgentStep.FAILED:
            raise RuntimeError(
                "Cannot transition from FAILED state."
            )

        allowed_steps = self.ALLOWED_TRANSITIONS.get(
            current_step,
            set(),
        )

        if next_step not in allowed_steps:
            raise RuntimeError(
                f"Invalid state transition: "
                f"{current_step.value} -> {next_step.value}"
            )

        state.current_step = next_step

    # ============================================================
    # EXECUTION TRACE
    # ============================================================

    def _add_trace_event(
        self,
        state: AgentState,
        *,
        stage: str,
        status: str,
        message: str | None = None,
        duration_ms: float | None = None,
        metadata: dict[str, object] | None = None,
    ):
        """
        Add a standardized execution-trace event to AgentState.

        Coordinator-level stages use attempt=0 because the
        Coordinator itself does not perform retry loops.

        Individual agents may append their own detailed events
        to the same execution trace.
        """

        event = ExecutionTraceEvent(
            stage=stage,
            status=status,
            attempt=0,
            message=message,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        state.execution_trace.append(
            event.model_dump(exclude_none=True)
        )

    # ============================================================
    # MAIN COORDINATOR FLOW
    # ============================================================

    def run(
        self,
        question: str,
        analytical_context: AnalyticalContext | None = None
    ):

        print("\n========== COORDINATOR ==========")
        print(f"User Question: {question}")

        state = AgentState(
            question=question,
            analytical_context=analytical_context
        )

        # ========================================================
        # 1. Intent
        # ========================================================
        #
        # IntentAgent owns its own execution trace.
        # Do NOT add duplicate Coordinator-level intent events.
        # ========================================================

        state = self.intent_agent.run(state)

        print(f"Intent: {state.intent}")

        if state.intent == QuestionIntent.UNKNOWN:

            state.mark_failure(
                "Unable to determine question intent."
            )

            return state

        # ========================================================
        # 2. Clarification
        # ========================================================
        #
        # ClarificationAgent owns its own execution trace.
        # Do NOT add duplicate Coordinator-level events.
        # ========================================================

        self._transition(
            state,
            AgentStep.CLARIFICATION,
        )

        clarification = self.clarification_agent.run(state)

        state.clarification = clarification

        if clarification.needs_clarification:

            print("Clarification required.")
            print(
                f"Question: {clarification.question}"
            )

            state.mark_success()

            return state

        # ========================================================
        # 3. Metadata
        # ========================================================
        #
        # MetadataAgent owns its own execution trace.
        # Do NOT add duplicate Coordinator-level events.
        # ========================================================

        self._transition(
            state,
            AgentStep.METADATA,
        )

        state = self.metadata_agent.run(state)

        if not state.metadata:

            state.mark_failure(
                "Metadata agent failed."
            )

            return state

        # ========================================================
        # 4. SQL
        # ========================================================
        #
        # Coordinator owns the high-level SQLAgent lifecycle.
        #
        # SQLAgent itself appends detailed internal events:
        #
        # generation
        # SQLGlot validation
        # PostgreSQL validation
        # semantic validation
        # context validation
        # repair
        #
        # SQLAgent's trace is appended to the existing trace.
        # ========================================================

        self._transition(
            state,
            AgentStep.SQL,
        )

        self._add_trace_event(
            state,
            stage="sql_agent",
            status="started",
            message="SQL agent execution started.",
            metadata={
                "component": self.sql_agent.__class__.__name__,
            },
        )

        sql_start = time.perf_counter()

        state = self.sql_agent.run(state)

        sql_duration_ms = (
            time.perf_counter() - sql_start
        ) * 1000

        if not state.sql or not state.sql.success:

            self._add_trace_event(
                state,
                stage="sql_agent",
                status="failed",
                message="SQL agent failed.",
                duration_ms=sql_duration_ms,
                metadata={
                    "component": self.sql_agent.__class__.__name__,
                },
            )

            if state.error is None and state.sql:
                state.mark_failure(
                    state.sql.errors
                )

            return state

        self._add_trace_event(
            state,
            stage="sql_agent",
            status="success",
            message="SQL agent completed successfully.",
            duration_ms=sql_duration_ms,
            metadata={
                "component": self.sql_agent.__class__.__name__,
            },
        )

        # ========================================================
        # 5. Analytics
        # ========================================================

        self._transition(
            state,
            AgentStep.ANALYTICS,
        )

        self._add_trace_event(
            state,
            stage="analytics",
            status="started",
            message="Analytics execution started.",
            metadata={
                "component": self.analytics_agent.__class__.__name__,
            },
        )

        analytics_start = time.perf_counter()

        state = self.analytics_agent.run(state)

        analytics_duration_ms = (
            time.perf_counter() - analytics_start
        ) * 1000

        if not state.analytics or not state.analytics.success:

            self._add_trace_event(
                state,
                stage="analytics",
                status="failed",
                message="Analytics agent failed.",
                duration_ms=analytics_duration_ms,
                metadata={
                    "component": self.analytics_agent.__class__.__name__,
                },
            )

            state.mark_failure(
                state.analytics.error
                if state.analytics
                else "Analytics agent failed."
            )

            return state

        self._add_trace_event(
            state,
            stage="analytics",
            status="success",
            message="Analytics completed successfully.",
            duration_ms=analytics_duration_ms,
            metadata={
                "component": self.analytics_agent.__class__.__name__,
            },
        )

        # ========================================================
        # 6. Answer Generation
        # ========================================================

        self._transition(
            state,
            AgentStep.ANSWER,
        )

        self._add_trace_event(
            state,
            stage="answer_generation",
            status="started",
            message="Answer generation started.",
            metadata={
                "component": self.answer_generator.__class__.__name__,
            },
        )

        answer_start = time.perf_counter()

        try:

            analyzed_result = (
                state.analytics.analysis
            )

            state.answer = (
                self.answer_generator.generate(
                    question=question,
                    analyzed_result=analyzed_result
                )
            )

            self._add_trace_event(
                state,
                stage="answer_generation",
                status="success",
                message="Answer generated successfully.",
                duration_ms=(
                    time.perf_counter() - answer_start
                ) * 1000,
                metadata={
                    "component": self.answer_generator.__class__.__name__,
                },
            )

        except Exception as exc:

            self._add_trace_event(
                state,
                stage="answer_generation",
                status="failed",
                message=f"Answer generation failed: {exc}",
                duration_ms=(
                    time.perf_counter() - answer_start
                ) * 1000,
                metadata={
                    "component": self.answer_generator.__class__.__name__,
                    "exception_type": exc.__class__.__name__,
                },
            )

            state.mark_failure(
                f"Answer generation failed: {exc}"
            )

            return state

        # ========================================================
        # 7. Completed
        # ========================================================

        self._add_trace_event(
            state,
            stage="coordinator",
            status="success",
            message="Data analyst workflow completed successfully.",
            metadata={
                "final_step": AgentStep.COMPLETED.value,
            },
        )

        self._transition(
            state,
            AgentStep.COMPLETED,
        )

        state.mark_success()

        return state