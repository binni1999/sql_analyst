"""Production-safe application logging configuration.

Logs are emitted to stdout/stderr so Docker and cloud log collectors can
capture them without managing log files inside the container.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|password|passwd|secret|token|credential|database[_-]?url|redis[_-]?url|connection[_-]?string)",
    re.IGNORECASE,
)
_URL_CREDENTIAL_RE = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<user>[^:/@\s]+):(?P<password>[^@\s]+)@",
    re.IGNORECASE,
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEY_RE.search(str(key)) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _URL_CREDENTIAL_RE.sub(r"\g<scheme>[REDACTED]@", value)
    return value


class JsonLogFormatter(logging.Formatter):
    """Emit one structured JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "structured_payload", None)

        if payload is None:
            payload = {
                "event": "log",
                "message": record.getMessage(),
            }

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": REQUEST_ID.get(),
            **_sanitize(payload),
        }

        if record.exc_info:
            output["exception"] = _sanitize(self.formatException(record.exc_info))

        return json.dumps(output, default=str, separators=(",", ":"))


class TextLogFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = REQUEST_ID.get()
        prefix = f" request_id={request_id}" if request_id else ""
        message = _sanitize(record.getMessage())
        return f"{self.formatTime(record)} | {record.levelname:<8} | {record.name}{prefix} | {message}"


def _resolve_level(level: str) -> int:
    resolved = getattr(logging, level.upper(), logging.INFO)
    return resolved if isinstance(resolved, int) else logging.INFO


def configure_logging(
    *,
    level: str = "INFO",
    environment: str = "development",
    log_format: str = "auto",
) -> None:
    """Configure application and Uvicorn loggers for stdout-based logging."""
    if log_format.lower() == "auto":
        log_format = "json" if environment.lower() in {"production", "prod"} else "text"

    formatter: logging.Formatter
    if log_format.lower() == "json":
        formatter = JsonLogFormatter()
    else:
        formatter = TextLogFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_resolve_level(level))

    # Uvicorn's default access/error handlers are replaced so container logs
    # use the same format as application logs.
    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(_resolve_level(level))
        logger.propagate = False

    # Request logging is handled by our middleware, which deliberately avoids
    # query strings and request bodies so secrets are not copied into logs.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.disabled = True

    logging.getLogger("httpx").setLevel(max(_resolve_level(level), logging.WARNING))

    # Useful for tests and for code that imports this module directly.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Write a sanitized structured application event."""
    logger.info(
        event,
        extra={
            "structured_payload": {
                "event": event,
                **fields,
            }
        },
    )
