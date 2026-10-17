from fastapi.testclient import TestClient

# pyrefly: ignore [missing-import]
from main import app
# pyrefly: ignore [missing-import]
from observability.metrics import metrics_registry
from logging_config import TextLogFormatter

def setup_function():
    metrics_registry.reset()


def teardown_function():
    metrics_registry.reset()


def test_successful_request_records_metrics():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["http.requests"] == 1
    assert snapshot["counters"]["http.successes"] == 1
    assert snapshot["counters"].get("http.client_errors", 0) == 0
    assert snapshot["counters"].get("http.server_errors", 0) == 0

    assert snapshot["timings"]["http.request_ms"]["count"] == 1


def test_not_found_request_records_client_error():
    client = TestClient(app)

    response = client.get("/does-not-exist")

    assert response.status_code == 404

    snapshot = metrics_registry.snapshot()

    assert snapshot["counters"]["http.requests"] == 1
    assert snapshot["counters"].get("http.successes", 0) == 0
    assert snapshot["counters"]["http.client_errors"] == 1
    assert snapshot["counters"].get("http.server_errors", 0) == 0

    assert snapshot["timings"]["http.request_ms"]["count"] == 1


def test_request_id_is_preserved():
    client = TestClient(app)

    request_id = "test-request-123"

    response = client.get(
        "/",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_id_is_generated_when_missing():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200

    generated_request_id = response.headers.get("X-Request-ID")

    assert generated_request_id
    assert len(generated_request_id) > 10



def test_metrics_endpoint_is_excluded_from_http_metrics():
    client = TestClient(app)

    # Record a baseline request first.
    response = client.get("/")
    assert response.status_code == 200

    before = metrics_registry.snapshot()

    response = client.get("/metrics")
    assert response.status_code == 200

    after = metrics_registry.snapshot()

    assert after["counters"] == before["counters"]
    assert after["timings"] == before["timings"]


def test_returned_server_error_records_server_error_metric():
    from fastapi import Response

    app.add_api_route(
        "/test-server-error-metrics",
        lambda: Response(status_code=500),
        methods=["GET"],
    )

    try:
        client = TestClient(app)
        response = client.get("/test-server-error-metrics")

        assert response.status_code == 500

        snapshot = metrics_registry.snapshot()

        assert snapshot["counters"]["http.requests"] == 1
        assert snapshot["counters"].get("http.successes", 0) == 0
        assert snapshot["counters"]["http.server_errors"] == 1
        assert snapshot["timings"]["http.request_ms"]["count"] == 1
    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None)
            != "/test-server-error-metrics"
        ]

def test_unexpected_exception_records_server_error_and_request_id(caplog):
    import logging

    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    # pyrefly: ignore [missing-import]
    from main import request_logging_middleware

    test_app = FastAPI()
    test_app.middleware("http")(request_logging_middleware)

    @test_app.get("/test-unexpected-error")
    async def raise_unexpected_error(request: Request):
        raise RuntimeError("simulated unexpected failure")

    request_id = "unexpected-error-test-123"

    with caplog.at_level(logging.ERROR):
        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.get(
                "/test-unexpected-error",
                headers={"X-Request-ID": request_id},
            )

    assert response.status_code == 500

    snapshot = metrics_registry.snapshot()
    assert snapshot["counters"]["http.requests"] == 1
    assert snapshot["counters"]["http.server_errors"] == 1
    assert snapshot["timings"]["http.request_ms"]["count"] == 1

   
    assert any(
        "request_failed" in record.getMessage()
        for record in caplog.records
    )

    assert any(
        getattr(record, "request_id", None) == request_id
        or request_id in record.getMessage()
        for record in caplog.records
    ) or request_id in caplog.text



def test_unexpected_exception_records_server_error_and_request_id():
    import logging

    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    # pyrefly: ignore [missing-import]
    from main import request_logging_middleware

    class FormattedLogCapture(logging.Handler):
        def __init__(self):
            super().__init__(logging.ERROR)
            self.messages = []

        def emit(self, record):
            self.messages.append(self.format(record))

    test_app = FastAPI()
    test_app.middleware("http")(request_logging_middleware)

    @test_app.get("/test-unexpected-error")
    async def raise_unexpected_error(request: Request):
        raise RuntimeError("simulated unexpected failure")

    request_id = "unexpected-error-test-123"
    handler = FormattedLogCapture()
    handler.setFormatter(TextLogFormatter())
    logger = logging.getLogger("datapilot.app")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)

    try:
        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.get(
                "/test-unexpected-error",
                headers={"X-Request-ID": request_id},
            )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert response.status_code == 500

    snapshot = metrics_registry.snapshot()
    assert snapshot["counters"]["http.requests"] == 1
    assert snapshot["counters"]["http.server_errors"] == 1
    assert snapshot["timings"]["http.request_ms"]["count"] == 1

    assert any(
        "request_failed" in message and request_id in message
        for message in handler.messages
    )

