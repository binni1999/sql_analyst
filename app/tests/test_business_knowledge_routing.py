from graph.routing import (
    route_after_business_knowledge,
    route_after_metadata,
)
from graph.state import create_initial_graph_state
from models.agent import MetadataResult


def test_route_after_metadata_goes_to_business_knowledge():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].metadata = MetadataResult(
        schemas=[],
        schema_text="TEST SCHEMA",
        metadata="TEST METADATA",
    )

    assert (
        route_after_metadata(state)
        == "business_knowledge"
    )


def test_route_after_business_knowledge_goes_to_sql():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    assert (
        route_after_business_knowledge(state)
        == "sql"
    )


def test_route_after_business_knowledge_ends_on_failure():

    state = create_initial_graph_state(
        question="Show revenue"
    )

    state["agent_state"].mark_failure(
        "Business knowledge retrieval failed"
    )

    assert (
        route_after_business_knowledge(state)
        == "end"
    )
