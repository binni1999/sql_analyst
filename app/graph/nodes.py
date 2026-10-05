import time

from langgraph.types import interrupt

from models.state import AgentState, AgentStep
from models.execution_trace import ExecutionTraceEvent


def _add_trace_event(
    agent_state: AgentState,
    stage: str,
    status: str,
    message: str,
    duration_ms: float | None = None,
    metadata: dict[str, object] | None = None,
):
    event = ExecutionTraceEvent(
        stage=stage,
        status=status,
        attempt=0,
        message=message,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )

    agent_state.execution_trace.append(event.model_dump())


def intent_node(state, intent_agent):
    agent_state: AgentState = state["agent_state"]

    agent_state = intent_agent.run(agent_state)

    if agent_state.intent == "unknown":
        agent_state.mark_failure(
            "Unable to determine question intent."
        )
        return {"agent_state": agent_state}

    agent_state.current_step = AgentStep.INITIALIZED

    return {"agent_state": agent_state}


def clarification_node(state, clarification_agent):
    agent_state: AgentState = state["agent_state"]

    clarification = clarification_agent.run(agent_state)

    agent_state.clarification = clarification
    agent_state.current_step = AgentStep.CLARIFICATION

    if clarification.needs_clarification:
        agent_state.mark_success()

    return {"agent_state": agent_state}


def metadata_node(state, metadata_agent):
    agent_state: AgentState = state["agent_state"]

    agent_state.current_step = AgentStep.METADATA

    agent_state = metadata_agent.run(agent_state)

    if not agent_state.metadata:
        agent_state.mark_failure(
            "Metadata agent failed."
        )

    return {"agent_state": agent_state}



def business_knowledge_node(
    state,
    business_knowledge_agent=None,
):
    """
    Retrieve business knowledge and attach it to AgentState.

    Business knowledge retrieval is an enrichment step.
    It does not modify the user question, analytical context,
    SQL, or downstream results.
    """
    agent_state: AgentState = state["agent_state"]

    # Keep the graph backward-compatible when no business
    # knowledge agent has been configured.
    if business_knowledge_agent is None:
        return {"agent_state": agent_state}

    try:
        result = business_knowledge_agent.run(agent_state)
        agent_state.business_knowledge = result

        return {"agent_state": agent_state}

    except Exception as exc:
        agent_state.mark_failure(
            f"Business knowledge retrieval failed: {exc}"
        )
        return {"agent_state": agent_state}


def sql_node(state, sql_agent):
    agent_state: AgentState = state["agent_state"]

    agent_state.current_step = AgentStep.SQL

    _add_trace_event(
        agent_state=agent_state,
        stage="sql_agent",
        status="started",
        message="SQL agent execution started.",
        metadata={
            "component": sql_agent.__class__.__name__,
        },
    )

    start_time = time.perf_counter()

    agent_state = sql_agent.run(agent_state)

    duration_ms = (
        time.perf_counter() - start_time
    ) * 1000

    if not agent_state.sql or not agent_state.sql.success:
        error = (
            agent_state.sql.errors
            if agent_state.sql
            else "SQL agent failed."
        )

        agent_state.mark_failure(error)

        _add_trace_event(
            agent_state=agent_state,
            stage="sql_agent",
            status="failed",
            message="SQL agent execution failed.",
            duration_ms=duration_ms,
            metadata={
                "component": sql_agent.__class__.__name__,
            },
        )

        return {"agent_state": agent_state}

    _add_trace_event(
        agent_state=agent_state,
        stage="sql_agent",
        status="success",
        message="SQL agent execution completed successfully.",
        duration_ms=duration_ms,
        metadata={
            "component": sql_agent.__class__.__name__,
        },
    )

    return {"agent_state": agent_state}


def analytics_node(state, analytics_agent):
    agent_state: AgentState = state["agent_state"]

    agent_state.current_step = AgentStep.ANALYTICS

    _add_trace_event(
        agent_state=agent_state,
        stage="analytics",
        status="started",
        message="Analytics agent execution started.",
        metadata={
            "component": analytics_agent.__class__.__name__,
        },
    )

    start_time = time.perf_counter()

    agent_state = analytics_agent.run(agent_state)

    duration_ms = (
        time.perf_counter() - start_time
    ) * 1000

    if not agent_state.analytics or not agent_state.analytics.success:
        error = (
            agent_state.analytics.error
            if agent_state.analytics
            else "Analytics agent failed."
        )

        agent_state.mark_failure(error)

        _add_trace_event(
            agent_state=agent_state,
            stage="analytics",
            status="failed",
            message="Analytics agent execution failed.",
            duration_ms=duration_ms,
            metadata={
                "component": analytics_agent.__class__.__name__,
            },
        )

        return {"agent_state": agent_state}

    _add_trace_event(
        agent_state=agent_state,
        stage="analytics",
        status="success",
        message="Analytics agent execution completed successfully.",
        duration_ms=duration_ms,
        metadata={
            "component": analytics_agent.__class__.__name__,
        },
    )

    return {"agent_state": agent_state}


def answer_node(state, answer_generator):
    agent_state: AgentState = state["agent_state"]

    agent_state.current_step = AgentStep.ANSWER

    _add_trace_event(
        agent_state=agent_state,
        stage="answer_generation",
        status="started",
        message="Answer generation started.",
        metadata={
            "component": answer_generator.__class__.__name__,
        },
    )

    start_time = time.perf_counter()

    if not agent_state.analytics:
        agent_state.mark_failure(
            "Analytics result is missing."
        )

        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        _add_trace_event(
            agent_state=agent_state,
            stage="answer_generation",
            status="failed",
            message="Answer generation failed because analytics result is missing.",
            duration_ms=duration_ms,
            metadata={
                "component": answer_generator.__class__.__name__,
            },
        )

        return {"agent_state": agent_state}

    try:
        analyzed_result = agent_state.analytics.analysis

        agent_state.answer = answer_generator.generate(
            question=agent_state.question,
            analyzed_result=analyzed_result,
        )

    except Exception as exc:
        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        agent_state.mark_failure(
            f"Answer generation failed: {exc}"
        )

        _add_trace_event(
            agent_state=agent_state,
            stage="answer_generation",
            status="failed",
            message="Answer generation failed.",
            duration_ms=duration_ms,
            metadata={
                "component": answer_generator.__class__.__name__,
                "exception_type": type(exc).__name__,
            },
        )

        return {"agent_state": agent_state}

    duration_ms = (
        time.perf_counter() - start_time
    ) * 1000

    _add_trace_event(
        agent_state=agent_state,
        stage="answer_generation",
        status="success",
        message="Answer generated successfully.",
        duration_ms=duration_ms,
        metadata={
            "component": answer_generator.__class__.__name__,
        },
    )

    agent_state.current_step = AgentStep.COMPLETED
    agent_state.mark_success()

    _add_trace_event(
        agent_state=agent_state,
        stage="completed",
        status="success",
        message="LangGraph workflow completed successfully.",
        metadata={
            "final_step": "completed",
        },
    )

    return {"agent_state": agent_state}


def risk_check_node(state, enable_interrupt: bool = False):
    from models.human_approval import HumanApprovalStatus

    agent_state: AgentState = state["agent_state"]

    # When a persistent LangGraph checkpoint resumes this node, the
    # risk assessment and PENDING status are already part of the
    # checkpoint. Do not duplicate the risk-check trace event.
    if agent_state.human_approval_status == HumanApprovalStatus.PENDING:
        if not enable_interrupt:
            return {"agent_state": agent_state}

        decision = interrupt({
            "type": "human_approval",
            "question": agent_state.human_approval_question
            or "Approve execution of the generated SQL?",
            "sql": agent_state.sql.sql if agent_state.sql else None,
            "risk_assessment": (
                agent_state.risk_assessment.model_dump()
                if agent_state.risk_assessment
                else None
            ),
        })

        return _apply_human_decision(agent_state, decision)

    from services.sql_risk_checker import SQLRiskChecker

    sql = agent_state.sql.sql if agent_state.sql else None

    if not sql:
        agent_state.mark_failure("SQL is missing for risk assessment.")
        return {"agent_state": agent_state}

    started = time.perf_counter()
    assessment = SQLRiskChecker().assess(sql)
    duration_ms = (time.perf_counter() - started) * 1000

    agent_state.risk_assessment = assessment

    if assessment.requires_approval:
        agent_state.human_approval_required = True
        agent_state.human_approval_status = HumanApprovalStatus.PENDING
        agent_state.human_approval_question = (
            "This query may be expensive or unusual. "
            "Review the generated SQL and approve execution if it is acceptable."
        )
        agent_state.current_step = AgentStep.HUMAN_APPROVAL

        _add_trace_event(
            agent_state=agent_state,
            stage="human_approval",
            status="pending",
            message="Human approval required before SQL execution.",
            duration_ms=duration_ms,
            metadata={
                "risk_level": assessment.risk_level,
                "reasons": assessment.reasons,
            },
        )

        # Dynamic interrupts are enabled only for checkpointed graphs.
        # The legacy no-checkpointer path keeps the Step 60 manual
        # approval flow intact.
        if not enable_interrupt:
            return {"agent_state": agent_state}

        decision = interrupt({
            "type": "human_approval",
            "question": agent_state.human_approval_question,
            "sql": sql,
            "risk_assessment": assessment.model_dump(),
        })

        return _apply_human_decision(agent_state, decision)

    agent_state.human_approval_required = False
    agent_state.human_approval_status = HumanApprovalStatus.NOT_REQUIRED

    _add_trace_event(
        agent_state=agent_state,
        stage="risk_check",
        status="success",
        message="SQL risk check passed; human approval is not required.",
        duration_ms=duration_ms,
        metadata={"risk_level": assessment.risk_level},
    )

    return {"agent_state": agent_state}


def _apply_human_decision(agent_state: AgentState, approved: bool):
    from models.human_approval import HumanApprovalStatus

    if approved:
        agent_state.human_approval_required = False
        agent_state.human_approval_status = HumanApprovalStatus.APPROVED
        agent_state.human_approval_question = None
        _add_trace_event(
            agent_state=agent_state,
            stage="human_approval",
            status="approved",
            message="Human approved SQL execution.",
            metadata={
                "risk_level": (
                    agent_state.risk_assessment.risk_level
                    if agent_state.risk_assessment
                    else None
                )
            },
        )
        return {"agent_state": agent_state}

    agent_state.human_approval_required = False
    agent_state.human_approval_status = HumanApprovalStatus.REJECTED
    agent_state.mark_failure("Human approval rejected SQL execution.")
    _add_trace_event(
        agent_state=agent_state,
        stage="human_approval",
        status="rejected",
        message="Human rejected SQL execution.",
    )
    return {"agent_state": agent_state}


def human_approval_node(state, approved: bool):
    from models.human_approval import HumanApprovalStatus

    agent_state: AgentState = state["agent_state"]
    agent_state.current_step = AgentStep.HUMAN_APPROVAL

    if approved:
        agent_state.human_approval_required = False
        agent_state.human_approval_status = HumanApprovalStatus.APPROVED
        agent_state.human_approval_question = None
        _add_trace_event(
            agent_state=agent_state,
            stage="human_approval",
            status="approved",
            message="Human approved SQL execution.",
            metadata={"risk_level": agent_state.risk_assessment.risk_level if agent_state.risk_assessment else None},
        )
        return {"agent_state": agent_state}

    agent_state.human_approval_required = False
    agent_state.human_approval_status = HumanApprovalStatus.REJECTED
    agent_state.mark_failure("Human approval rejected SQL execution.")
    _add_trace_event(
        agent_state=agent_state,
        stage="human_approval",
        status="rejected",
        message="Human rejected SQL execution.",
    )
    return {"agent_state": agent_state}
