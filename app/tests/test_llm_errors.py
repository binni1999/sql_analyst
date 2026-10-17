from types import SimpleNamespace

import pytest

from services.llm_errors import (
    is_llm_rate_limit_error,
    user_facing_llm_error,
)


@pytest.mark.parametrize(
    "exc",
    [
        Exception("rate_limit_exceeded"),
        Exception("Daily tokens per day quota reached"),
        Exception("HTTP 429 Too Many Requests"),
        type("RateLimitError", (Exception,), {})("provider quota reached"),
        type(
            "ProviderError",
            (Exception,),
            {"status_code": 429},
        )("provider request rejected"),
        type(
            "ProviderError",
            (Exception,),
            {"response": SimpleNamespace(status_code=429)},
        )("provider request rejected"),
    ],
)
def test_detects_llm_rate_limit_errors(exc):
    assert is_llm_rate_limit_error(exc)


def test_rate_limit_message_for_sql_generation():
    message = user_facing_llm_error(
        Exception("tokens per day quota reached"),
        "sql_generation",
    )

    assert "SQL generation is temporarily unavailable" in message
    assert "try again later" in message
    assert "tokens per day" not in message


def test_rate_limit_message_for_answer_generation():
    message = user_facing_llm_error(
        Exception("HTTP 429 Too Many Requests"),
        "answer_generation",
    )

    assert "answer generation is temporarily unavailable" in message
    assert "try again later" in message


def test_non_rate_limit_error_returns_safe_sql_generation_message():
    message = user_facing_llm_error(
        ValueError("provider secret or internal response details"),
        "sql_generation",
    )

    assert message == (
        "SQL generation failed because the language-model provider "
        "encountered an error. Please try again later."
    )
    assert "provider secret" not in message
    assert "internal response details" not in message


def test_non_rate_limit_answer_error_returns_safe_message():
    message = user_facing_llm_error(
        ValueError("sensitive provider response"),
        "answer_generation",
    )

    assert message == (
        "Answer generation failed because the language-model provider "
        "encountered an error. Please try again later."
    )
    assert "sensitive provider response" not in message


def test_regular_exception_is_not_classified_as_rate_limit():
    assert not is_llm_rate_limit_error(
        ValueError("invalid generated SQL")
    )
