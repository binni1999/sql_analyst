
# pyrefly: ignore [missing-import]

from services.conversation_id import (
    generate_conversation_id
)

from graph.workflow import DataAnalystGraph

from models.response import DataAnalystResponse
from models.state import AgentState
from models.request import DataAnalystRequest

from services.question_validator import QuestionValidator
from services.conversation_service import ConversationService
from agents.clarification_resolver import ClarificationResolver
from agents.follow_up_resolver import FollowUpResolver
from agents.analytical_context_extractor import (
    AnalyticalContextExtractor
)
from services.execution_summary import ExecutionSummaryService
from services.memory_service import ConversationMemoryService
from security.input_guardrails import PromptInjectionGuardrail

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
        # Optional Step 58 capability. The existing graph does not invoke it;
        # callers may opt into model-selected tools without changing SQLAgent.
        self.tool_executor = tool_executor
        # Step 67.5: input-layer prompt-injection defense. Keep this optional
        # for backward compatibility with existing service test doubles.
        self.prompt_guardrail = prompt_guardrail or PromptInjectionGuardrail()

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
            print("\n========== CHECKPOINT RECOVERY DIAGNOSTIC ==========")
            print("CONVERSATION ID:", conversation_id)

            try:
                checkpoint_state = get_checkpoint_state(conversation_id)

                print("CHECKPOINT STATE:", checkpoint_state)

                if checkpoint_state is not None:
                    checkpoint_agent_state = checkpoint_state.get("agent_state")
                    checkpoint_interrupted = checkpoint_state.get(
                        "interrupted",
                        False,
                    )

                    print(
                        "CHECKPOINT AGENT STATE:",
                        checkpoint_agent_state,
                    )
                    print(
                        "CHECKPOINT INTERRUPTED:",
                        checkpoint_interrupted,
                    )

                    if checkpoint_agent_state is not None:
                        print(
                            "HUMAN APPROVAL STATUS:",
                            checkpoint_agent_state.human_approval_status,
                        )
                        print(
                            "HUMAN APPROVAL REQUIRED:",
                            checkpoint_agent_state.human_approval_required,
                        )
                        print(
                            "CURRENT STEP:",
                            checkpoint_agent_state.current_step,
                        )
                        print(
                            "QUESTION:",
                            checkpoint_agent_state.question,
                        )

                    # IMPORTANT:
                    # When LangGraph pauses inside interrupt(), the node has
                    # not returned its updated AgentState yet. Therefore the
                    # persisted AgentState can still show
                    # human_approval_status=NOT_REQUIRED and current_step=SQL.
                    #
                    # The durable source of truth for a paused HITL workflow
                    # is the LangGraph checkpoint's active interrupt/task.
                    if (
                        checkpoint_agent_state is not None
                        and checkpoint_interrupted
                    ):
                        conversation.waiting_for_human_approval = True
                        conversation.pending_agent_state = (
                            checkpoint_agent_state.model_dump(mode="json")
                        )
                        self.conversation_service.save(conversation)

                        print(
                            "CHECKPOINT RECOVERY: HITL INTERRUPT RECOVERED"
                        )
                    elif checkpoint_agent_state is not None:
                        print(
                            "CHECKPOINT RECOVERY: STATE EXISTS "
                            "BUT IS NOT AN ACTIVE HITL INTERRUPT"
                        )
                else:
                    print("CHECKPOINT RECOVERY: NO CHECKPOINT FOUND")

            except Exception as exc:
                print(
                    "CHECKPOINT RECOVERY ERROR:",
                    type(exc).__name__,
                    str(exc),
                )
                raise

            print("====================================================\n")

        # ----------------------------------
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
                    execution_trace=[],
                    
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

            if has_previous_context:

                try:

                    resolved_question = (
                        self.follow_up_resolver.resolve(
                            conversation,
                            request.question
                        )
                    )

                except ValueError:

                    # If the follow-up resolver cannot
                    # resolve the question, preserve
                    # the original question rather
                    # than failing the entire request.

                    resolved_question = (
                        request.question
                    )

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
                resolved_question
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

            return DataAnalystResponse(
                success=False,
                question=request.question,
                conversation_id=conversation_id,
                answer=None,
                sql=(
                    state.sql.sql
                    if state.sql and state.sql.sql
                    else None
                ),
                result=None,
                error=state.error,
                execution_trace=state.execution_trace,
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
            execution_trace=state.execution_trace,
            execution_summary=execution_summary,
        )


    def _run_graph(
        self,
        question: str,
        analytical_context,
        conversation_id: str,
    ):
        kwargs = {
            "analytical_context": analytical_context,
        }

        # Existing test doubles and non-persistent callers keep the Step 60
        # signature. The production DataAnalystGraph enables the durable
        # thread_id only when a checkpointer is configured.
        if getattr(self.graph, "checkpointer", None) is not None:
            kwargs["conversation_id"] = conversation_id

        return self.graph.run(question, **kwargs)


    def _update_analytical_context(
        self,
        conversation,
        resolved_question: str
    ):
        context = (
            self.analytical_context_extractor.extract(
                question=resolved_question,
                previous_context=(
                    conversation.analytical_context
                )
            )
        )

        conversation.analytical_context = context

        self.conversation_service.save(
            conversation
        )

        return context
