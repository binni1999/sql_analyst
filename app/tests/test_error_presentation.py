"""Regression tests for safe, user-facing analysis errors."""

from services.data_analyst_service import DataAnalystService


def test_provider_rate_limit_maps_to_retryable_friendly_error():
    code = DataAnalystService._classify_error(
        "HTTP 429 rate limit exceeded; provider request failed"
    )
    assert code == "LLM_PROVIDER_UNAVAILABLE"
    message = DataAnalystService._safe_error_message(
        "HTTP 429 rate limit exceeded; provider request failed"
    )
    assert "temporarily unavailable" in message.lower()
    assert "429" not in message


def test_unknown_schema_object_maps_to_friendly_message():
    code = DataAnalystService._classify_error(
        'column "customer_favorite_color" does not exist'
    )
    assert code == "SCHEMA_VALIDATION_FAILED"
    message = DataAnalystService._safe_error_message(
        'column "customer_favorite_color" does not exist'
    )
    assert "table or column" in message.lower()
    assert "customer_favorite_color" not in message


def test_unexpected_provider_exception_is_not_exposed_to_user():
    secret_like_error = "provider failed with api_key=super-secret-value"
    message = DataAnalystService._safe_error_message(secret_like_error)
    assert "super-secret-value" not in message
    assert message == "Something went wrong while analyzing your question. Please try again."
