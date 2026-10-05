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