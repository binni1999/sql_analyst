import sys
from pathlib import Path

# Add app directory to sys.path so imports resolve correctly when run directly
app_dir = Path(__file__).resolve().parent.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# pyrefly: ignore [missing-import]
from factory import create_data_analyst_service
from graph.workflow import DataAnalystGraph


QUESTION = "Show the top 5 products by revenue"


def main():

    print("\n")
    print("=" * 70)
    print("LANGGRAPH REAL EXECUTION TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Create the real application service
    # ---------------------------------------------------------

    service = create_data_analyst_service()

    # ---------------------------------------------------------
    # 2. Get the production Coordinator
    #
    # The Coordinator already contains the real agent instances.
    # We reuse those instances for LangGraph.
    # ---------------------------------------------------------

    coordinator = service.coordinator

    # ---------------------------------------------------------
    # 3. Build LangGraph using the REAL agents
    # ---------------------------------------------------------

    graph = DataAnalystGraph(
        intent_agent=coordinator.intent_agent,
        clarification_agent=(
            coordinator.clarification_agent
        ),
        metadata_agent=coordinator.metadata_agent,
        sql_agent=coordinator.sql_agent,
        analytics_agent=coordinator.analytics_agent,
        answer_generator=coordinator.answer_generator,
    )

    # ---------------------------------------------------------
    # 4. Extract analytical context exactly as the service does
    # ---------------------------------------------------------

    analytical_context = (
        service.analytical_context_extractor.extract(
            question=QUESTION,
            previous_context=None,
        )
    )

    print("\nQuestion:")
    print(QUESTION)

    print("\nAnalytical Context:")
    print(
        analytical_context.model_dump(
            exclude_none=True
        )
    )

    # ---------------------------------------------------------
    # 5. Execute LangGraph
    # ---------------------------------------------------------

    state = graph.run(
        question=QUESTION,
        analytical_context=analytical_context,
    )

    # ---------------------------------------------------------
    # 6. Print final state
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("LANGGRAPH RESULT")
    print("=" * 70)

    print("\nSuccess:")
    print(state.success)

    print("\nCurrent Step:")
    print(state.current_step)

    print("\nIntent:")
    print(state.intent)

    print("\nSQL:")
    if state.sql:
        print(state.sql.sql)
    else:
        print(None)

    print("\nAnalytics:")
    if state.analytics:
        print(state.analytics.analysis)
    else:
        print(None)

    print("\nAnswer:")
    print(state.answer)

    print("\nError:")
    print(state.error)

    # ---------------------------------------------------------
    # 7. Execution trace
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("EXECUTION TRACE")
    print("=" * 70)

    for index, event in enumerate(
        state.execution_trace,
        start=1,
    ):
        print(
            f"\n[{index}] "
            f"{event.get('stage')} "
            f"| {event.get('status')}"
        )

        if event.get("message"):
            print(
                f"    message: "
                f"{event.get('message')}"
            )

        if event.get("duration_ms") is not None:
            print(
                f"    duration_ms: "
                f"{event.get('duration_ms')}"
            )

        if event.get("metadata"):
            print(
                f"    metadata: "
                f"{event.get('metadata')}"
            )

    print("\n")
    print("=" * 70)
    print("END")
    print("=" * 70)


if __name__ == "__main__":
    main()