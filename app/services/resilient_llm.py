
"""Provider fallback wrapper for LangChain chat models.

The primary model remains the existing Groq model. If it fails with a
transient provider error (including HTTP 429 rate limits), compatible backup
providers are attempted in order. Non-provider errors are not hidden by
fallback, which helps surface prompt/schema/application bugs.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _get_http_status(error: BaseException) -> int | None:
    """Extract an HTTP status code from common provider exception shapes."""
    status = getattr(error, "status_code", None)

    if status is None:
        response = getattr(error, "response", None)
        status = getattr(response, "status_code", None)

    return status if isinstance(status, int) else None


def _is_transient_provider_error(error: BaseException) -> bool:
    """Return True only for failures where switching provider may help."""
    name = type(error).__name__.lower()
    message = str(error).lower()
    status = _get_http_status(error)

    if status == 429 or status in (408, 409, 425) or (
        status is not None and status >= 500
    ):
        return True

    if any(
        token in name
        for token in (
            "ratelimit",
            "timeout",
            "connection",
            "serviceunavailable",
            "apitimeout",
        )
    ):
        return True

    return any(
        token in message
        for token in (
            "rate_limit_exceeded",
            "rate limit reached",
            "too many requests",
            "status code 429",
            "error code: 429",
            "http 429",
            "429 rate limit",
            "service unavailable",
            "temporarily unavailable",
            "connection error",
            "connection reset",
            "timed out",
            "timeout",
        )
    )


class _FallbackRunnable:
    """Invoke provider-specific LangChain runnables with ordered fallback."""

    def __init__(self, builders: list[tuple[str, Callable[[], Any]]]):
        self._builders = builders

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        if not self._builders:
            raise RuntimeError("No LLM providers are configured.")

        for index, (provider_name, builder) in enumerate(self._builders):
            try:
                runnable = builder()

                if config is None:
                    return runnable.invoke(input, **kwargs)

                return runnable.invoke(input, config=config, **kwargs)

            except Exception as error:
                status = _get_http_status(error)
                error_type = type(error).__name__
                transient = _is_transient_provider_error(error)
                is_last = index == len(self._builders) - 1

                if not transient:
                    logger.exception(
                        "LLM provider %s failed with a non-transient error; "
                        "fallback will not be attempted "
                        "(error_type=%s, status=%s)",
                        provider_name,
                        error_type,
                        status,
                    )
                    raise

                if is_last:
                    logger.error(
                        "All configured LLM providers failed; "
                        "final_provider=%s error_type=%s status=%s",
                        provider_name,
                        error_type,
                        status,
                    )
                    raise

                next_provider = self._builders[index + 1][0]
                logger.warning(
                    "LLM provider %s failed with a transient error; "
                    "trying configured fallback %s "
                    "(error_type=%s, status=%s)",
                    provider_name,
                    next_provider,
                    error_type,
                    status,
                )

        # Defensive guard: the loop normally returns or raises.
        raise RuntimeError("LLM invocation finished without a result.")


class ResilientChatModel:
    """Small compatibility wrapper for the LangChain chat-model methods used here."""

    def __init__(
        self,
        primary: Any,
        fallbacks: list[tuple[str, Any]] | None = None,
    ):
        self.primary = primary
        self.fallbacks = fallbacks or []

    def _models(self) -> list[tuple[str, Any]]:
        return [("primary", self.primary), *self.fallbacks]

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return _FallbackRunnable(
            [
                (name, lambda model=model: model)
                for name, model in self._models()
            ]
        ).invoke(input, config=config, **kwargs)

    def with_structured_output(
        self,
        schema: Any,
        **kwargs: Any,
    ) -> _FallbackRunnable:
        return _FallbackRunnable(
            [
                (
                    name,
                    lambda model=model: model.with_structured_output(
                        schema, **kwargs
                    ),
                )
                for name, model in self._models()
            ]
        )

    def bind_tools(self, tools: Any, **kwargs: Any) -> _FallbackRunnable:
        return _FallbackRunnable(
            [
                (
                    name,
                    lambda model=model: model.bind_tools(tools, **kwargs),
                )
                for name, model in self._models()
            ]
        )

    def __getattr__(self, name: str) -> Any:
        # Preserve access to provider metadata expected by LangChain callers.
        return getattr(self.primary, name)


def build_resilient_chat_model(primary: Any) -> ResilientChatModel:
    """Create a primary model plus whichever backup providers are configured.

    Backups are opt-in through credentials. Missing optional integrations do not
    prevent the application from starting; they are logged and skipped.
    """
    fallbacks: list[tuple[str, Any]] = []
    callback_handlers = getattr(primary, "callbacks", None)

    fallback_order = [
        item.strip().lower()
        for item in os.getenv("LLM_FALLBACK_ORDER", "openai,gemini").split(",")
        if item.strip()
    ]

    for provider in fallback_order:
        try:
            if provider == "openai" and os.getenv("OPENAI_API_KEY"):
                from langchain_openai import ChatOpenAI

                model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
                fallbacks.append(
                    (
                        f"openai:{model}",
                        ChatOpenAI(
                            model=model,
                            api_key=os.environ["OPENAI_API_KEY"],
                            temperature=0,
                            max_retries=0,
                            callbacks=callback_handlers,
                        ),
                    )
                )

            elif provider == "gemini" and os.getenv("GEMINI_API_KEY"):
                from langchain_google_genai import ChatGoogleGenerativeAI

                model = os.getenv(
                    "GEMINI_FALLBACK_MODEL",
                    "gemini-2.5-flash",
                )
                fallbacks.append(
                    (
                        f"gemini:{model}",
                        ChatGoogleGenerativeAI(
                            model=model,
                            google_api_key=os.environ["GEMINI_API_KEY"],
                            temperature=0,
                            max_retries=0,
                            callbacks=callback_handlers,
                        ),
                    )
                )

        except ImportError:
            logger.warning(
                "Configured LLM fallback provider %s is skipped because "
                "its LangChain integration is not installed.",
                provider,
            )
        except Exception:
            # A misconfigured backup must not make the primary unusable.
            logger.exception(
                "Could not initialize configured LLM fallback provider %s",
                provider,
            )

    if fallbacks:
        logger.info(
            "LLM fallback providers enabled: %s",
            ", ".join(name for name, _ in fallbacks),
        )
    else:
        logger.warning(
            "No LLM backup provider is enabled. Configure OPENAI_API_KEY "
            "and/or GEMINI_API_KEY, and install the corresponding LangChain "
            "integration to enable automatic fallback."
        )

    return ResilientChatModel(primary, fallbacks)
