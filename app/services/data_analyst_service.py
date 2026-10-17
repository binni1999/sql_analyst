import logging
import uuid

logger = logging.getLogger(__name__)


# pyrefly: ignore [missing-import]

from services.conversation_id import (
    generate_conversation_id
)

from graph.workflow import DataAnalystGraph

from models.response import DataAnalystResponse
from models.state import AgentState
from models.request import DataAnalystRequest
from observability.metrics import metrics_registry
from services.question_validator import QuestionValidator
from services.conversation_service import ConversationService
from agents.clarification_resolver import ClarificationResolver
from agents.follow_up_resolver import FollowUpResolver
from agents.analytical_context_extractor import (
    AnalyticalContextExtractor
)
from services.observability import ObservabilityService
from services.execution_summary import ExecutionSummaryService
from services.memory_service import ConversationMemoryService
from security.input_guardrails import PromptInjectionGuardrail
from security.data_access_guardrail import DataAccessGuardrail

class DataAnalystService:

    def __init__(
        self,
        graph: DataAnalystGraph,
        question_validator: QuestionValidator,
        conversation_service: ConversationService,
        clarification_resolver: ClarificationResolver,
        follow_up_resolver: FollowUpResolver,
        analytical_context_extractor: AnalyticalContextExtractor,
        tool_executor=None,
        memory_service: ConversationMemoryService | None = None,
        prompt_guardrail: PromptInjectionGuardrail | None = None,
        data_access_guardrail: DataAccessGuardrail | None = None,
        observability_service: ObservabilityService | None = None,
    ):
        self.graph = graph
        self.question_validator = question_validator
        self.conversation_service = (
            conversation_service
        )
        self.clarification_resolver = (
            clarification_resolver
        )
        self.follow_up_resolver = (
            follow_up_resolver
        )
        self.analytical_context_extractor = (
            analytical_context_extractor
        )

        self.observability_service = (
            observability_service or ObservabilityService()
        )
        # Optional Step 58 capability. The existing graph does not invoke it;
        # callers may opt into model-selected tools without changing SQLAgent.
        self.tool_executor = tool_executor
        # Step 67.5: input-layer prompt-injection defense. Keep this optional
        # for backward compatibility with existing service test doubles.
        self.prompt_guardrail = prompt_guardrail or PromptInjectionGuardrail()
        # Enforce data-access policy before any graph/LLM/SQL execution.
        self.data_access_guardrail = data_access_guardrail or DataAccessGuardrail()

        # Step 63: explicit conversation-memory layer. Keep this optional so
        # existing unit-test doubles and callers remain backward compatible.
        self.memory_service = (
            memory_service
            or ConversationMemoryService()
        )

    def ask(
        self,
        request: DataAnalystRequest
    ):

        # ----------------------------------
        # 1. Get or create conversation
        # ----------------------------------

        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation_id = generate_conversation_id()

        conversation = (
            self.conversation_service
            .get_or_create(conversation_id)
        )

        # ----------------------------------
        # 1b. Recover a checkpointed HITL pause
        # ----------------------------------
        # ConversationService is intentionally still lightweight/in-memory.
        # The LangGraph checkpoint is the durable source of truth for a paused
        # graph, so recover the pending state after an API/process restart.
        get_checkpoint_state = getattr(
            self.graph,
            "get_checkpoint_state",
            None,
        )
        if not conversation.waiting_for_human_approval and get_checkpoint_state:
            try:
                checkpoint_state = get_checkpoint_state(conversation_id)

                if checkpoint_state is not None:
                    checkpoint_agent_state = checkpoint_state.get("agent_state")
                    checkpoint_interrupted = checkpoint_state.get(
                        "interrupted",
                        False,
                    )

                    # When LangGraph pauses inside interrupt(), the persisted
                    # AgentState may not yet reflect the pending approval.
                    # The active checkpoint interrupt is the source of truth.
                    if (
                        checkpoint_agent_state is not None
                        and checkpoint_interrupted
                    ):
                        conversation.waiting_for_human_approval = True
                        conversation.pending_agent_state = (
                            checkpoint_agent_state.model_dump(mode="json")
                        )
                        self.conversation_service.save(conversation)

            except Exception:
                raise
        # 2. Add user message to history
        # ----------------------------------
        # A pending HITL response may be a short command such as
        # "Approve" or "Reject", not an analytical question. Record it
        # before handling the pending checkpoint so question validation
        # cannot incorrectly reject the human decision.

        self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.question
        )

        # ----------------------------------
        # 3. Handle pending human approval
        # ----------------------------------

        if conversation.waiting_for_human_approval:

            if request.human_approval is None:
                pending_state = AgentState.model_validate(
                    conversation.pending_agent_state
                )
                execution_summary = ExecutionSummaryService.build(
                    execution_trace=pending_state.execution_trace,
                    successful=False,
                )
                return DataAnalystResponse(
                    success=True,
                    question=request.question,
                    conversation_id=conversation_id,
                    sql=(pending_state.sql.sql if pending_state.sql else None),
                    needs_human_approval=True,
                    human_approval_question=pending_state.human_approval_question,
                    risk_assessment=(
                        pending_state.risk_assessment.model_dump()
                        if pending_state.risk_assessment
                        else None
                    ),
                    execution_trace=pending_state.execution_trace,
                    execution_summary=execution_summary,
                )

            if conversation.pending_agent_state is None:
                return DataAnalystResponse(
                    success=False,
                    question=request.question,
                    conversation_id=conversation_id,
                    error="No pending human-approval state is available.",
                )

            pending_state = AgentState.model_validate(
                conversation.pending_agent_state
            )

            if getattr(self.graph, "checkpointer", None) is not None:
                state = self.graph.resume_after_human_approval(
                    pending_state,
                    request.human_approval,
                    conversation_id=conversation_id,
                )
            else:
                state = self.graph.resume_after_human_approval(
                    pending_state,
                    request.human_approval,
                )

            conversation.waiting_for_human_approval = False
            conversation.pending_agent_state = None
            self.conversation_service.save(conversation)

            execution_summary = ExecutionSummaryService.build(
                execution_trace=state.execution_trace,
                successful=state.success,
            )

            if not state.success:
                error_message = (
                    str(state.error)
                    if state.error
                    else "Human approval rejected SQL execution."
                )
                self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=error_message,
                )
                return DataAnalystResponse(
                    success=False,
                    question=request.question,
                    conversation_id=conversation_id,
                    sql=(state.sql.sql if state.sql else None),
                    error=state.error,
                    execution_trace=state.execution_trace,
                    execution_summary=execution_summary,
                )

            if state.answer:
                self.memory_service.remember_turn(
                    conversation,
                    user_question=request.question,
                    resolved_question=(
                        conversation.resolved_question
                        or state.question
                    ),
                    analytical_context=conversation.analytical_context,
                    answer=state.answer,
                )

                self.conversation_service.save(
                    conversation
                )

                self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=state.answer,
                )

            return DataAnalystResponse(
                success=True,
                question=request.question,
                conversation_id=conversation_id,
                answer=state.answer,
                sql=(state.sql.sql if state.sql else None),
                result=(state.analytics.analysis if state.analytics else None),
                execution_trace=state.execution_trace,
                execution_summary=execution_summary,
            )

        # ----------------------------------
        # 4. Validate a new analytical question
        # ----------------------------------
        # Validation belongs after the HITL branch because an approval
        # response is a workflow command rather than a new SQL question.

        validation = (
            self.question_validator.validate(
                request.question
            )
        )

        if not validation["valid"]:

            return DataAnalystResponse(
                success=False,
                question=request.question,
                conversation_id=conversation_id,
                answer=None,
                sql=None,
                result=None,
                error=validation["errors"],
                error_code="INVALID_QUESTION",
                execution_trace=[]
            )

        # ----------------------------------
        # 4b. Prompt/input security guardrail
        # ----------------------------------
        # HITL approval commands are handled above and are intentionally not
        # treated as analytical prompts. Every new analytical/clarification
        # input is checked before it reaches an LLM or agent.
        prompt_security = self.prompt_guardrail.validate(request.question)

        if not prompt_security.allowed:
            security_errors = [
                violation.message
                for violation in prompt_security.violations
            ]
            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content="Input rejected by prompt security guardrails.",
            )
            return DataAnalystResponse(
                success=False,
                question=request.question,
                conversation_id=conversation_id,
                error=security_errors,
                execution_trace=[],
            )

        # ----------------------------------
        # 4c. Data-access confidentiality policy
        # ----------------------------------
        # This check must run before clarification resolution or graph invocation,
        # so a blocked request cannot reach SQL generation, repair, or execution.
        access_policy = self.data_access_guardrail.validate(request.question)
        if not access_policy.allowed:
            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=access_policy.reason or "Request denied by data-access policy.",
            )
            return DataAnalystResponse(
                success=False,
                question=request.question,
                conversation_id=conversation_id,
                answer=None,
                sql=None,
                result=None,
                error=access_policy.reason or "Request denied by data-access policy.",
                error_code="REQUEST_BLOCKED",
                # pyrefly: ignore[unbound-name]
                execution_trace=[],
            )

        # ----------------------------------
        # 5. Handle clarification response
        # ----------------------------------

        if conversation.waiting_for_clarification:

            try:

                resolved_question = (
                    self.clarification_resolver.resolve(
                        conversation,
                        request.question
                    )
                )

            except ValueError as exc:

                clarification_question = None
                clarification_options = []

                if conversation.clarification:

                    clarification_question = (
                        conversation
                        .clarification
                        .question
                    )

                    clarification_options = (
                        conversation
                        .clarification
                        .options
                    )

                assistant_message = (
                    clarification_question
                    or str(exc)
                )

                self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_message
                )

                return DataAnalystResponse(
                    success=False,
                    question=request.question,
                    conversation_id=conversation_id,
                    answer=None,
                    sql=None,
                    result=None,
                    error=str(exc),
                    needs_clarification=True,
                    clarification_question=(
                        clarification_question
                    ),
                    clarification_options=(
                        clarification_options
                    ),
                    # pyrefly: ignore[unbound-name]
                    execution_trace=state.execution_trace or [],
                    
                )

            # Store resolved question

            conversation.resolved_question = (
                resolved_question
            )

            # Conversation is no longer waiting
            # for clarification

            conversation.waiting_for_clarification = (
                False
            )

            self._update_analytical_context(
                conversation,
                resolved_question
            )

            # ----------------------------------
            # Run normal agent pipeline
            # using resolved question
            # ----------------------------------

            state = self._run_graph(
                resolved_question,
                conversation.analytical_context,
                conversation_id,
            )
            execution_summary = ExecutionSummaryService.build(
                execution_trace=state.execution_trace,
                successful=state.success,
            )

        else:

            # ----------------------------------
            # 5. Handle normal question OR
            # conversational follow-up
            # ----------------------------------

            # Because the current user message has
            # already been added to history, a
            # conversation with more than one message
            # has previous conversational context.

            has_previous_context = (
                len(conversation.history) > 1
            )

            is_follow_up = False
            if has_previous_context:

                try:
                    classifier = getattr(
                        self.follow_up_resolver,
                        "is_follow_up",
                        None,
                    )
                    is_follow_up = (
                        bool(classifier(request.question))
                        if classifier is not None
                        else True
                    )
                    resolved_question = (
                        self.follow_up_resolver.resolve(
                            conversation,
                            request.question
                        )
                        if is_follow_up
                        else request.question
                    )

                except ValueError:

                    # If the follow-up resolver cannot
                    # resolve the question, preserve
                    # the original question rather
                    # than failing the entire request.

                    resolved_question = (
                        request.question
                    )
                    is_follow_up = False

            else:

                # First request in the conversation.

                resolved_question = (
                    request.question
                )

            # Store the resolved question so that
            # subsequent follow-ups can use it.

            conversation.resolved_question = (
                resolved_question
            )

            self._update_analytical_context(
                conversation,
                resolved_question,
                preserve_previous=is_follow_up,
            )

            # ----------------------------------
            # Run agent pipeline
            # ----------------------------------

            state = self._run_graph(
                resolved_question,
                conversation.analytical_context,
                conversation_id,
            )
            execution_summary = ExecutionSummaryService.build(
                execution_trace=state.execution_trace,
                successful=state.success,
            )
            #execution_summary=execution_summary

        # ----------------------------------
        # 6. Clarification required
        # ----------------------------------

        if (
            state.clarification
            and state.clarification.needs_clarification
        ):

            # Store clarification state

            conversation.original_question = (
                request.question
            )

            conversation.clarification = (
                state.clarification
            )

            conversation.waiting_for_clarification = (
                True
            )

            self.conversation_service.save(
                conversation
            )

            # Store assistant clarification
            # in conversation history

            clarification_text = (
                state.clarification.question
                or "Please provide clarification."
            )

            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=clarification_text
            )

            return DataAnalystResponse(
                success=True,
                question=request.question,
                conversation_id=conversation_id,
                answer=None,
                sql=None,
                result=None,
                error=None,
                needs_clarification=True,
                clarification_question=(
                    state.clarification.question
                ),
                clarification_options=(
                    state.clarification.options
                ),
                execution_trace=state.execution_trace,
                execution_summary=execution_summary,
            )

        # ----------------------------------
        # 7. Human approval required
        # ----------------------------------

        if state.human_approval_required:
            conversation.waiting_for_human_approval = True
            conversation.pending_agent_state = state.model_dump(mode="json")
            self.conversation_service.save(conversation)

            return DataAnalystResponse(
                success=True,
                question=request.question,
                conversation_id=conversation_id,
                answer=None,
                sql=(state.sql.sql if state.sql else None),
                result=None,
                error=None,
                needs_human_approval=True,
                human_approval_question=state.human_approval_question,
                risk_assessment=(
                    state.risk_assessment.model_dump()
                    if state.risk_assessment
                    else None
                ),
                execution_trace=state.execution_trace,
                execution_summary=execution_summary,
            )

        # ----------------------------------
        # 8. Normal failure
        # ----------------------------------

        if not state.success:

            error_message = (
                str(state.error)
                if state.error
                else "Agent pipeline failed."
            )

            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=error_message
            )

            # Keep a deterministic fallback answer only when answer generation
            # failed after analysis succeeded. Do not expose partial answers for
            # SQL, schema, authorization, or execution failures.
            error_text = str(state.error or "").lower()
            fallback_answer = None
            if (
                state.answer
                and state.analytics is not None
                and "answer generation failed" in error_text
            ):
                fallback_answer = state.answer

            return DataAnalystResponse(
                success=False,
                question=request.question,
                conversation_id=conversation_id,
                answer=fallback_answer,
                sql=None,
                result=None,
                error=self._safe_error_message(state.error),
                error_code=self._classify_error(state.error),
                error_reference=self._error_reference(),
                execution_trace=state.execution_trace or [],
                execution_summary=execution_summary,
            )

        # ----------------------------------
        # 8. Extract successful result
        # ----------------------------------

        sql = None

        if state.sql:
            sql = state.sql.sql

        result = None

        if state.analytics:
            result = state.analytics.analysis

        answer = state.answer

        # ----------------------------------
        # 9. Update conversation memory
        # ----------------------------------

        self.memory_service.remember_turn(
            conversation,
            user_question=request.question,
            resolved_question=(
                conversation.resolved_question
                or request.question
            ),
            analytical_context=conversation.analytical_context,
            answer=answer,
        )

        self.conversation_service.save(
            conversation
        )

        # ----------------------------------
        # 10. Store assistant answer
        # ----------------------------------

        if answer:

            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=answer
            )

        # ----------------------------------
        # 10. Successful response
        # ----------------------------------

        # return DataAnalystResponse(
        #     success=True,
        #     question=request.question,
        #     conversation_id=conversation_id,
        #     answer=answer,
        #     sql=sql,
        #     result=result,
        #     error=None,
        #     needs_clarification=False,
        #     clarification_question=None,
        #     clarification_options=[],
        #     execution_trace=state.execution_trace or [],
        #     execution_summary=execution_summary,
        # )

        return DataAnalystResponse(
            success=True,
            question=request.question,
            conversation_id=conversation_id,
            answer=answer,
            sql=sql,
            result=result,
            error=None,
            needs_clarification=False,
            clarification_question=None,
            clarification_options=[],
            execution_trace=state.execution_trace or [],
            execution_summary=execution_summary,
        )



    
    @staticmethod
    def _error_reference() -> str:
        return uuid.uuid4().hex[:10].upper()

    @staticmethod
    def _classify_error(error) -> str:
        text = str(error or "").lower()
        if any(term in text for term in ("429", "rate limit", "too many requests", "timeout", "timed out", "temporarily unavailable", "connection reset")):
            return "LLM_PROVIDER_UNAVAILABLE"
        if any(term in text for term in ("unknown column", "column not found", "does not exist", "unknown table", "relation")):
            return "SCHEMA_VALIDATION_FAILED"
        if any(term in text for term in ("security", "not allowed", "permission denied", "rejected by")):
            return "REQUEST_BLOCKED"
        if any(term in text for term in ("sql", "generation", "query")):
            return "SQL_GENERATION_FAILED"
        return "ANALYSIS_FAILED"

    @staticmethod
    def _safe_error_message(error) -> str:
        code = DataAnalystService._classify_error(error)
        messages = {
            "LLM_PROVIDER_UNAVAILABLE": (
                "Our analysis service is temporarily unavailable due to a "
                "provider rate limit or temporary outage. Please try again shortly."
            ),
            "SCHEMA_VALIDATION_FAILED": "We couldn't find a requested table or column in your database. Check the name and try again.",
            "REQUEST_BLOCKED": "This request couldn't be completed because it doesn't meet the data-access or security policy.",
            "SQL_GENERATION_FAILED": "We couldn't turn your question into a valid database query. Try rephrasing it.",
            "ANALYSIS_FAILED": "Something went wrong while analyzing your question. Please try again.",
        }
        return messages[code]

    def _run_graph(self, question, analytical_context, conversation_id):
        kwargs = {"analytical_context": analytical_context}
        if getattr(self.graph, "checkpointer", None) is not None:
            kwargs["conversation_id"] = conversation_id

        state = None
        graph_succeeded = False

        metrics_registry.increment("agent.graph_executions")

        try:
            with metrics_registry.timer("agent.graph_execution_ms"):
                with self.observability_service.capture(
                    conversation_id=conversation_id,
                ) as observability_context:
                    try:
                        state = self.graph.run(question, **kwargs)
                        graph_succeeded = bool(
                            getattr(state, "success", False)
                        )
                        return state
                    except Exception:
                        # Log detailed diagnostics, but let the service caller
                        # decide how to handle the failure. Re-raising preserves
                        # the graph execution contract and makes failures visible
                        # to callers/tests instead of disguising them as a normal
                        # AgentState failure.
                        logger.exception(
                            "DataPilot graph execution failed",
                            extra={"conversation_id": conversation_id},
                        )
                        raise
                    finally:
                        observability_context.summary(
                            execution_trace=getattr(
                                state, "execution_trace", None
                            )
                        )
        finally:
            metrics_registry.increment(
                "agent.graph_successes"
                if graph_succeeded
                else "agent.graph_failures"
            )



    def _update_analytical_context(
        self,
        conversation,
        resolved_question: str,
        preserve_previous: bool = True,
    ):
        context = (
            self.analytical_context_extractor.extract(
                question=resolved_question,
                previous_context=(
                    conversation.analytical_context
                    if preserve_previous
                    else None
                )
            )
        )

        conversation.analytical_context = context

        self.conversation_service.save(
            conversation
        )

        return context

