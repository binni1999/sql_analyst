from agents.sql_agent import SQLAgent

from models.agent import (
    MetadataResult,
    SQLResult
)

from models.state import AgentState


class MockSQLAgent(SQLAgent):

    def __init__(self):
        pass

    def generate_valid_sql(
        self,
        question,
        schema,
        schemas,
        metadata
    ):

        return {
            "success": True,
            "sql": "SELECT 1",
            "attempts": 1,
            "errors": []
        }


def test_sql_agent_updates_state():

    agent = MockSQLAgent()

    metadata = MetadataResult(
        schemas=[],
        schema_text="TEST SCHEMA",
        metadata="TEST METADATA"
    )

    state = AgentState(
        question="Show revenue",
        metadata=metadata
    )

    result = agent.run(state)

    assert result is state

    assert result.question == (
        "Show revenue"
    )

    assert result.sql is not None

    assert isinstance(
        result.sql,
        SQLResult
    )

    assert result.sql.success is True

    assert result.sql.sql == (
        "SELECT 1"
    )
    assert result.success is True
    assert result.error is None


def test_sql_agent_fails_without_metadata():

    agent = MockSQLAgent()

    state = AgentState(
        question="Show revenue"
    )

    result = agent.run(state)

    assert result is state

    assert result.sql is not None

    assert result.sql.success is False

    assert result.error is not None