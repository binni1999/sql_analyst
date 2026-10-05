
from agents.analytics_agent import AnalyticsAgent

from models.agent import (
    AnalyticsResult,
    SQLResult
)

from models.state import AgentState


class MockSQLExecutor:

    def execute(self, sql):

        assert sql == "SELECT 1"

        return {
            "success": True,
            "columns": ["result"],
            "rows": [[1]],
            "error": None
        }


class MockResultAnalyzer:

    def analyze(self, result):

        assert result["success"] is True

        return {
            "row_count": 1,
            "columns": ["result"],
            "data": [
                {
                    "result": 1
                }
            ],
            "is_empty": False
        }


class MockFailingSQLExecutor:

    def execute(self, sql):

        return {
            "success": False,
            "columns": [],
            "rows": [],
            "error": "Database execution failed"
        }


def test_analytics_agent_updates_state():

    agent = AnalyticsAgent(
        sql_executor=MockSQLExecutor(),
        result_analyzer=MockResultAnalyzer()
    )

    sql_result = SQLResult(
        success=True,
        sql="SELECT 1",
        attempts=1,
        errors=[]
    )

    state = AgentState(
        question="Show revenue",
        sql=sql_result
    )

    result = agent.run(state)

    assert result is state

    assert result.analytics is not None

    assert isinstance(
        result.analytics,
        AnalyticsResult
    )

    assert result.analytics.success is True

    assert result.analytics.analysis is not None

    assert result.analytics.analysis["row_count"] == 1
    assert result.success is True

    assert result.error is None


def test_analytics_agent_fails_without_sql():

    agent = AnalyticsAgent(
        sql_executor=MockSQLExecutor(),
        result_analyzer=MockResultAnalyzer()
    )

    state = AgentState(
        question="Show revenue"
    )

    result = agent.run(state)

    assert result is state

    assert result.analytics is not None

    assert result.analytics.success is False

    assert result.analytics.error == (
        "SQL Agent has not produced a result."
    )

    assert result.success is False


def test_analytics_agent_handles_sql_failure():

    agent = AnalyticsAgent(
        sql_executor=MockSQLExecutor(),
        result_analyzer=MockResultAnalyzer()
    )

    sql_result = SQLResult(
        success=False,
        sql=None,
        attempts=4,
        errors=[
            "Unable to generate valid SQL"
        ]
    )

    state = AgentState(
        question="Show revenue",
        sql=sql_result
    )

    result = agent.run(state)

    assert result is state

    assert result.analytics is not None

    assert result.analytics.success is False

    assert result.analytics.error == (
        "SQL Agent failed."
    )

    assert result.success is False


def test_analytics_agent_handles_execution_failure():

    agent = AnalyticsAgent(
        sql_executor=MockFailingSQLExecutor(),
        result_analyzer=MockResultAnalyzer()
    )

    sql_result = SQLResult(
        success=True,
        sql="SELECT 1",
        attempts=1,
        errors=[]
    )

    state = AgentState(
        question="Show revenue",
        sql=sql_result
    )

    result = agent.run(state)

    assert result is state

    assert result.analytics is not None

    assert result.analytics.success is False

    assert result.analytics.error == (
        "Database execution failed"
    )

    assert result.analytics.execution is not None

    assert result.success is False