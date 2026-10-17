def is_llm_rate_limit_error(exc: Exception) -> bool:
    """Identify common LLM-provider rate-limit exceptions."""
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)

    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)

    if status_code == 429 or type(exc).__name__ == "RateLimitError":
        return True

    message = str(exc).lower()
    indicators = (
        "rate_limit_exceeded",
        "rate limit",
        "too many requests",
        "tokens per day",
        "requests per minute",
        "tokens per minute",
        "error code: 429",
        "http 429",
    )

    return any(indicator in message for indicator in indicators)


def user_facing_llm_error(exc: Exception, stage: str) -> str:
    """Return a safe, actionable message for an LLM failure."""
    if is_llm_rate_limit_error(exc):
        if stage == "answer_generation":
            return (
                "The query processing completed, but answer generation is "
                "temporarily unavailable because the language-model provider "
                "rate limit was reached. Please try again later."
            )

        return (
            "SQL generation is temporarily unavailable because the "
            "language-model provider rate limit was reached. "
            "Please try again later."
        )

    if stage == "sql_generation":
        return (
            "SQL generation failed because the language-model provider "
            "encountered an error. Please try again later."
        )

    if stage == "answer_generation":
        return (
            "Answer generation failed because the language-model provider "
            "encountered an error. Please try again later."
        )

    return f"{stage.replace('_', ' ').capitalize()} failed."