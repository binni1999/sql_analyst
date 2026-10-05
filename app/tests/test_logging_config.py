import json
import logging

from logging_config import JsonLogFormatter, _sanitize


def test_sanitize_redacts_sensitive_keys_and_url_credentials():
    payload = {
        "api_key": "secret-value",
        "database_url": "postgresql://postgres:secret@db:5432/app",
        "safe": "value",
    }

    sanitized = _sanitize(payload)

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["database_url"] == "[REDACTED]"
    assert sanitized["safe"] == "value"


def test_json_formatter_outputs_structured_payload():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="datapilot.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="ignored",
        args=(),
        exc_info=None,
    )
    record.structured_payload = {
        "event": "test_event",
        "status": "ok",
        "api_key": "do-not-log",
    }

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "test_event"
    assert payload["status"] == "ok"
    assert payload["api_key"] == "[REDACTED]"
    assert "timestamp" in payload
