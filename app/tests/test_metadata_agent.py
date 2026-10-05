from agents.metadata_agent import MetadataAgent

from models.agent import MetadataResult
from models.state import AgentState


class MockDatabase:

    def get_full_schema(self):

        return [
            {
                "table": "customers",
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "integer"
                    },
                    {
                        "name": "name",
                        "type": "character varying"
                    }
                ],
                "primary_keys": [
                    "customer_id"
                ],
                "foreign_keys": []
            }
        ]


class MockMetadataService:

    def build_metadata_text(self):

        return "TEST METADATA"


def test_metadata_agent_updates_state():

    agent = MetadataAgent(
        metadata_service=MockMetadataService(),
        db=MockDatabase()
    )

    state = AgentState(
        question="Show customers"
    )

    result = agent.run(state)

    # Agent should return AgentState
    assert isinstance(
        result,
        AgentState
    )

    # Question should remain unchanged
    assert result.question == (
        "Show customers"
    )

    # Metadata should now exist
    assert result.metadata is not None

    # Metadata should be MetadataResult
    assert isinstance(
        result.metadata,
        MetadataResult
    )

    # Verify schema
    assert result.metadata.schema_text == (
        "\nTABLE customers\n"
        "\nColumns:\n"
        "- customer_id integer\n"
        "- name character varying\n"
        "\nPrimary Keys:\n"
        "- customer_id\n"
    )

    # Verify metadata text
    assert result.metadata.metadata == (
        "TEST METADATA"
    )
    assert result.success is True
    assert result.error is None

def test_metadata_agent_adds_execution_trace():

    agent = MetadataAgent(
        metadata_service=MockMetadataService(),
        db=MockDatabase()
    )

    state = AgentState(
        question="Show customers"
    )

    result = agent.run(state)

    assert len(result.execution_trace) == 2
    assert result.execution_trace[0]["stage"] == "metadata"
    assert result.execution_trace[0]["status"] == "started"
    assert result.execution_trace[1]["stage"] == "metadata"
    assert result.execution_trace[1]["status"] == "success"
    assert result.execution_trace[1]["metadata"]["table_count"] == 1
    assert result.execution_trace[1]["metadata"]["metadata_available"] is True


def test_metadata_agent_runs_schema_and_business_metadata_in_parallel():
    import threading

    barrier = threading.Barrier(2)

    class ParallelDatabase(MockDatabase):
        def get_full_schema(self):
            barrier.wait(timeout=2)
            return super().get_full_schema()

    class ParallelMetadataService(MockMetadataService):
        def build_metadata_text(self):
            barrier.wait(timeout=2)
            return super().build_metadata_text()

    agent = MetadataAgent(
        metadata_service=ParallelMetadataService(),
        db=ParallelDatabase(),
    )

    state = AgentState(question="Show customers")
    result = agent.run(state)

    assert result.metadata is not None
    assert result.metadata.metadata == "TEST METADATA"
    assert result.metadata.schemas[0]["table"] == "customers"
    assert result.execution_trace[0]["metadata"]["parallel_branches"] == [
        "schema_retrieval",
        "business_metadata_retrieval",
    ]
    assert result.execution_trace[1]["metadata"]["parallel_branches_completed"] == 2
