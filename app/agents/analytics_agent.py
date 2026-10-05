from models.agent import AnalyticsResult
from models.state import AgentState


class AnalyticsAgent:

    def __init__(
        self,
        sql_executor,
        result_analyzer
    ):
        self.sql_executor = sql_executor
        self.result_analyzer = result_analyzer

    def run(self, state: AgentState):

        print("\n" + "-" * 60)
        print("ANALYTICS AGENT")
        print("-" * 60)

        sql_result = state.sql

        if sql_result is None:

            state.analytics = AnalyticsResult(
                success=False,
                error="SQL Agent has not produced a result."
            )

            state.mark_failure(
                state.analytics.error
            )

            return state

        if not sql_result.success:

            state.analytics = AnalyticsResult(
                success=False,
                error="SQL Agent failed."
            )

            state.mark_failure(
                state.analytics.error
            )

            return state

        sql = sql_result.sql

        if not sql:

            state.analytics = AnalyticsResult(
                success=False,
                error="SQL Agent returned no SQL."
            )

            state.mark_failure(
                state.analytics.error
            )

            return state

        execution_result = self.sql_executor.execute(sql)

        if not execution_result["success"]:

            state.analytics = AnalyticsResult(
                success=False,
                execution=execution_result,
                error=execution_result["error"]
            )

            state.mark_failure(
                state.analytics.error
            )

            return state

        analyzed_result = self.result_analyzer.analyze(
            execution_result
        )

        state.analytics = AnalyticsResult(
            success=True,
            execution=execution_result,
            analysis=analyzed_result
        )

        state.mark_success()

        return state