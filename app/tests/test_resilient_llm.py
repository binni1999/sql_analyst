from unittest.mock import MagicMock

import pytest

from services.resilient_llm import ResilientChatModel, _is_transient_provider_error


class ProviderRateLimitError(Exception):
    status_code = 429


def test_rate_limit_is_classified_as_transient():
    assert _is_transient_provider_error(ProviderRateLimitError("rate limited"))


def test_validation_error_is_not_classified_as_transient():
    assert not _is_transient_provider_error(ValueError("invalid SQL schema"))


def test_invoke_uses_backup_after_primary_rate_limit():
    primary = MagicMock()
    primary.invoke.side_effect = ProviderRateLimitError("rate limit reached")
    backup = MagicMock()
    backup.invoke.return_value = "backup response"

    model = ResilientChatModel(primary, [("backup", backup)])

    assert model.invoke("hello") == "backup response"
    primary.invoke.assert_called_once_with("hello")
    backup.invoke.assert_called_once_with("hello")


def test_invoke_does_not_hide_non_provider_errors():
    primary = MagicMock()
    primary.invoke.side_effect = ValueError("bad input")
    backup = MagicMock()
    model = ResilientChatModel(primary, [("backup", backup)])

    with pytest.raises(ValueError, match="bad input"):
        model.invoke("hello")
    backup.invoke.assert_not_called()


def test_structured_output_uses_backup_after_provider_failure():
    primary = MagicMock()
    primary_structured = MagicMock()
    primary_structured.invoke.side_effect = ProviderRateLimitError("429 rate limit")
    primary.with_structured_output.return_value = primary_structured

    backup = MagicMock()
    backup_structured = MagicMock()
    backup_structured.invoke.return_value = {"sql": "SELECT 1"}
    backup.with_structured_output.return_value = backup_structured

    model = ResilientChatModel(primary, [("backup", backup)])
    result = model.with_structured_output(dict).invoke([("human", "question")])

    assert result == {"sql": "SELECT 1"}
    primary.with_structured_output.assert_called_once_with(dict)
    backup.with_structured_output.assert_called_once_with(dict)



def test_all_provider_failures_are_logged(caplog):
    import logging

    primary = MagicMock()
    primary.invoke.side_effect = ProviderRateLimitError("rate limit reached")

    backup = MagicMock()
    backup.invoke.side_effect = ProviderRateLimitError("backup rate limit reached")

    model = ResilientChatModel(primary, [("backup", backup)])

    with caplog.at_level(logging.ERROR, logger="services.resilient_llm"):
        with pytest.raises(ProviderRateLimitError):
            model.invoke("hello")

    assert "All configured LLM providers failed" in caplog.text
    assert "final_provider=backup" in caplog.text
    primary.invoke.assert_called_once()
    backup.invoke.assert_called_once()
