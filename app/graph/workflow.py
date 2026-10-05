from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from graph.nodes import (
    answer_node,
    analytics_node,
    clarification_node,
    intent_node,
    metadata_node,
    sql_node,
    risk_check_node,
    human_approval_node,
    business_knowledge_node,
)

from graph.routing import (
    route_after_analytics,
    route_after_clarification,
    route_after_intent,
    route_after_metadata,
    route_after_sql,
    route_after_risk_check,
    route_after_human_approval,
    route_after_business_knowledge,
)

from graph.state import (
    GraphState,
    create_initial_graph_state,
)


class DataAnalystGraph:

    def __init__(
        self,
        intent_agent,
        clarification_agent,
        metadata_agent,
        sql_agent,
        analytics_agent,
        answer_generator,
        business_knowledge_agent=None,
        checkpointer=None,
    ):
        self.intent_agent = intent_agent
        self.clarification_agent = clarification_agent
        self.metadata_agent = metadata_agent
        self.sql_agent = sql_agent
        self.analytics_agent = analytics_agent
        self.answer_generator = answer_generator
        self.business_knowledge_agent = business_knowledge_agent
        self.checkpointer = checkpointer

        self.graph = self._build_graph()
        self.human_approval_graph = self._build_human_approval_graph()

    def _build_graph(self):

        builder = StateGraph(GraphState)

        builder.add_node(
            "intent",
            lambda state: intent_node(
                state,
                self.intent_agent,
            ),
        )

        builder.add_node(
            "clarification",
            lambda state: clarification_node(
                state,
                self.clarification_agent,
            ),
        )

        builder.add_node(
            "metadata",
            lambda state: metadata_node(
                state,
                self.metadata_agent,
            ),
        )

        builder.add_node(
            "business_knowledge",
            lambda state: business_knowledge_node(
                state,
                self.business_knowledge_agent,
            ),
        )

        builder.add_node(
            "sql",
            lambda state: sql_node(
                state,
                self.sql_agent,
            ),
        )

        builder.add_node(
            "risk_check",
            lambda state: risk_check_node(
                state,
                enable_interrupt=self.checkpointer is not None,
            ),
        )

        builder.add_node(
            "analytics",
            lambda state: analytics_node(
                state,
                self.analytics_agent,
            ),
        )

        builder.add_node(
            "answer",
            lambda state: answer_node(
                state,
                self.answer_generator,
            ),
        )

        builder.add_edge(
            START,
            "intent",
        )

        builder.add_conditional_edges(
            "intent",
            route_after_intent,
            {
                "clarification": "clarification",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "clarification",
            route_after_clarification,
            {
                "metadata": "metadata",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "metadata",
            route_after_metadata,
            {
                "business_knowledge": "business_knowledge",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "business_knowledge",
            route_after_business_knowledge,
            {
                "sql": "sql",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "sql",
            route_after_sql,
            {
                "analytics": "risk_check",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "risk_check",
            route_after_risk_check,
            {
                "analytics": "analytics",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "analytics",
            route_after_analytics,
            {
                "answer": "answer",
                "end": END,
            },
        )

        builder.add_edge(
            "answer",
            END,
        )

        if self.checkpointer is not None:
            return builder.compile(checkpointer=self.checkpointer)

        return builder.compile()

    def _build_human_approval_graph(self):
        builder = StateGraph(GraphState)

        builder.add_node(
            "human_approval",
            lambda state: human_approval_node(
                state,
                bool(state.get("human_approval")),
            ),
        )
        builder.add_node(
            "analytics",
            lambda state: analytics_node(
                state,
                self.analytics_agent,
            ),
        )
        builder.add_node(
            "answer",
            lambda state: answer_node(
                state,
                self.answer_generator,
            ),
        )

        builder.add_edge(START, "human_approval")
        builder.add_conditional_edges(
            "human_approval",
            route_after_human_approval,
            {"analytics": "analytics", "end": END},
        )
        builder.add_edge("analytics", "answer")
        builder.add_edge("answer", END)
        return builder.compile()

    def run(
        self,
        question: str,
        analytical_context=None,
        conversation_id: str | None = None,
    ):

        initial_state = create_initial_graph_state(
            question=question,
            analytical_context=analytical_context,
        )

        config = None
        if self.checkpointer is not None:
            if not conversation_id:
                raise ValueError(
                    "conversation_id is required when checkpointing is enabled."
                )
            config = {"configurable": {"thread_id": conversation_id}}

        result = self.graph.invoke(
            initial_state,
            config=config,
        )

        return result["agent_state"]

    def get_checkpoint_state(self, conversation_id):
        if self.checkpointer is None:
            return None

        from models.human_approval import HumanApprovalStatus
        from models.state import AgentStep

        config = {"configurable": {"thread_id": conversation_id}}
        snapshot = self.graph.get_state(config)

        values = snapshot.values

        if not values or "agent_state" not in values:
            return None

        agent_state = values["agent_state"]

        interrupted = False
        interrupt_payload = None

        for task in snapshot.tasks:
            task_interrupts = getattr(task, "interrupts", None)

            if task_interrupts:
                interrupted = True

                interrupt_info = task_interrupts[0]

                # LangGraph Interrupt objects expose the payload through
                # the `value` attribute.
                interrupt_payload = getattr(
                    interrupt_info,
                    "value",
                    None,
                )

                break

        # When risk_check_node() calls interrupt(), LangGraph checkpoints
        # the state BEFORE the interrupted node returns. Therefore the
        # persisted AgentState may still contain:
        #
        #   human_approval_status = NOT_REQUIRED
        #   human_approval_required = False
        #   current_step = SQL
        #
        # The active interrupt is the durable indication that the workflow
        # is waiting for human approval.
        #
        # Reconstruct the logical pending HITL state for callers that
        # recover the conversation after a process restart.
        if interrupted:
            agent_state = agent_state.model_copy(deep=True)

            agent_state.human_approval_required = True
            agent_state.human_approval_status = HumanApprovalStatus.PENDING
            agent_state.current_step = AgentStep.HUMAN_APPROVAL

            if isinstance(interrupt_payload, dict):
                question = interrupt_payload.get("question")

                if question:
                    agent_state.human_approval_question = question

                risk_assessment = interrupt_payload.get("risk_assessment")

                if (
                    risk_assessment is not None
                    and agent_state.risk_assessment is None
                ):
                    try:
                        from models.risk_assessment import RiskAssessment

                        agent_state.risk_assessment = (
                            RiskAssessment.model_validate(risk_assessment)
                        )
                    except Exception:
                        # The checkpoint already contains the persisted
                        # AgentState. If the interrupt payload cannot be
                        # reconstructed into RiskAssessment, preserve the
                        # existing state rather than failing recovery.
                        pass

        return {
            "agent_state": agent_state,
            "interrupted": interrupted,
        }

    # def resume_after_human_approval(
    #     self,
    #     agent_state,
    #     approved: bool,
    #     conversation_id: str | None = None,
    # ):
    #     if self.checkpointer is not None:
    #         if not conversation_id:
    #             raise ValueError(
    #                 "conversation_id is required when checkpointing is enabled."
    #             )
    #         config = {"configurable": {"thread_id": conversation_id}}
    #         result = self.graph.invoke(
    #             Command(resume=approved),
    #             config=config,
    #         )
    #         return result["agent_state"]

    #     # Backward-compatible path for unit tests/local callers that construct
    #     # DataAnalystGraph without a checkpointer.
    #     graph_state = {
    #         "agent_state": agent_state,
    #         "human_approval": approved,
    #     }
    #     result = self.human_approval_graph.invoke(graph_state)
    #     return result["agent_state"]

    def resume_after_human_approval(self, agent_state, approved, conversation_id=None):
        if self.checkpointer is not None:
            if not conversation_id:
                raise ValueError("conversation_id is required when checkpointing is enabled.")

            config = {"configurable": {"thread_id": conversation_id}}

            print("\n========== RESUME DIAGNOSTIC ==========")
            snapshot = self.graph.get_state(config)
            print("RESUME THREAD:", conversation_id)
            print("RESUME NEXT:", snapshot.next)
            print("RESUME TASKS:", snapshot.tasks)
            print("RESUME VALUES:", snapshot.values)
            print("========================================\n")

            result = self.graph.invoke(
                Command(resume=approved),
                config=config,
            )

            return result["agent_state"]

    
