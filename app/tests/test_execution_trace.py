from models.execution_trace import ExecutionTraceEvent


def test_execution_trace_event_minimal():

    event = ExecutionTraceEvent(
        stage="generation",
        status="success",
    )

    assert event.stage == "generation"
    assert event.status == "success"
    assert event.attempt == 0
    assert event.message is None
    assert event.error_type is None
    assert event.metadata == {}


def test_execution_trace_event_with_all_fields():

    event = ExecutionTraceEvent(
        stage="context_validation",
        status="failed",
        attempt=2,
        message="Expected DESC ordering but found ASC.",
        error_type="context",
        metadata={
            "validator": "ContextValidator",
        },
    )

    assert event.stage == "context_validation"
    assert event.status == "failed"
    assert event.attempt == 2
    assert event.message == (
        "Expected DESC ordering but found ASC."
    )
    assert event.error_type == "context"
    assert event.metadata == {
        "validator": "ContextValidator",
    }


def test_execution_trace_event_serializes_to_dict():

    event = ExecutionTraceEvent(
        stage="generation",
        status="success",
        attempt=0,
        message="SQL generated successfully.",
    )

    data = event.model_dump(exclude_none=True)

    assert data == {
        "stage": "generation",
        "status": "success",
        "attempt": 0,
        "message": "SQL generated successfully.",
        "metadata": {},
    }


def test_execution_trace_event_default_metadata_is_isolated():

    event_one = ExecutionTraceEvent(
        stage="generation",
        status="success",
    )

    event_two = ExecutionTraceEvent(
        stage="repair",
        status="success",
    )

    event_one.metadata["model"] = "test-model"

    assert event_one.metadata == {
        "model": "test-model",
    }

    assert event_two.metadata == {}


def test_execution_trace_event_supports_retry_attempts():

    event = ExecutionTraceEvent(
        stage="repair",
        status="success",
        attempt=2,
    )

    assert event.attempt == 2

def test_execution_trace_event_supports_duration_ms():
    event = ExecutionTraceEvent(
        stage="sql_agent",
        status="success",
        duration_ms=1842.7,
    )

    assert event.duration_ms == 1842.7


def test_execution_trace_event_duration_ms_defaults_to_none():
    event = ExecutionTraceEvent(
        stage="sql_agent",
        status="started",
    )

    assert event.duration_ms is None


def test_execution_trace_event_serializes_duration_ms():
    event = ExecutionTraceEvent(
        stage="sql_agent",
        status="success",
        duration_ms=125.5,
    )

    data = event.model_dump()

    assert data["duration_ms"] == 125.5

