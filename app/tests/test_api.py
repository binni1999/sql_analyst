from fastapi.testclient import TestClient

# pyrefly: ignore [missing-import]
from main import app


client = TestClient(app)


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy"
    }


def test_ask_valid_question():

    response = client.post(
        "/api/ask",
        json={
            "question": "Show the top 5 products by revenue"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["question"] == (
        "Show the top 5 products by revenue"
    )

    assert data["answer"] is not None

    assert data["sql"] is not None

    assert data["result"] is not None

    assert data["error"] is None

    # ----------------------------------
    # Execution trace
    # ----------------------------------

    assert "execution_trace" in data

    assert len(data["execution_trace"]) > 0

    for event in data["execution_trace"]:

        assert "stage" in event

        assert "status" in event

    # ----------------------------------
    # Execution duration metrics
    # ----------------------------------

    timed_stages = {
        "sql_agent",
        "analytics",
        "answer_generation"
    }

    timed_events = [
        event
        for event in data["execution_trace"]
        if event["stage"] in timed_stages
        and event["status"] in {
            "success",
            "failed"
        }
    ]

    assert len(timed_events) == 3

    for event in timed_events:

        assert "duration_ms" in event

        assert event["duration_ms"] >= 0


def test_question_too_short():

    response = client.post(
        "/api/ask",
        json={
            "question": "Hi"
        }
    )

    assert response.status_code == 422


def test_missing_question():

    response = client.post(
        "/api/ask",
        json={}
    )

    assert response.status_code == 422


def test_whitespace_question():

    response = client.post(
        "/api/ask",
        json={
            "question": "   "
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert data["answer"] is None

    assert data["sql"] is None

    assert data["result"] is None

    assert data["error"] is not None


def test_ask_ambiguous_question():

    response = client.post(
        "/api/ask",
        json={
            "question": "Show me the best products"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["needs_clarification"] is True

    assert (
        data["clarification_question"]
        is not None
    )

    assert len(
        data["clarification_options"]
    ) > 0

    assert data["sql"] is None

    assert data["answer"] is None



from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def test_request_id_is_returned_to_client():
    response = client.get(
        "/health",
        headers={"X-Request-ID": "test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_request_id_is_generated_when_missing():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")



def test_unexpected_exception_returns_server_error():
    test_app = FastAPI()

    @test_app.get("/test-error")
    def trigger_error():
        raise RuntimeError("Simulated internal failure")

    test_client = TestClient(
        test_app,
        raise_server_exceptions=False,
    )

    response = test_client.get("/test-error")

    assert response.status_code == 500



def test_metrics_registry_tracks_server_error_metrics():
    # pyrefly: ignore [missing-import]
    from observability.metrics import MetricsRegistry

    registry = MetricsRegistry()

    registry.increment("http.requests")
    registry.increment("http.server_errors")
    registry.observe("http.request_ms", 25.0)

    snapshot = registry.snapshot()

    assert snapshot["counters"]["http.requests"] == 1
    assert snapshot["counters"]["http.server_errors"] == 1
    assert snapshot["timings"]["http.request_ms"]["count"] == 1
    assert snapshot["timings"]["http.request_ms"]["total_ms"] == 25.0
