from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Any, Iterator

from models.observability import (
    LLMCallObservation,
    ModelObservation,
    ObservabilitySummary,
    StageObservation,
)
_CURRENT_STAGE: ContextVar[str | None] = ContextVar(
    "datapilot_observability_stage",
    default=None,
)

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - dependency is required by the project
    BaseCallbackHandler = object


_LOGGER = logging.getLogger("datapilot.observability")
_CURRENT_CONTEXT: ContextVar["ObservabilityContext | None"] = ContextVar(
    "datapilot_observability_context",
    default=None,
)


def _env_float(name: str) -> float:
    try:
        return float(os.getenv(name, "0"))
    except (TypeError, ValueError):
        return 0.0


class JsonObservabilityFormatter(logging.Formatter):
    """Serialize observability records as one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "observability_payload", None)
        if payload is None:
            payload = {
                "event": "log",
                "level": record.levelname,
                "message": record.getMessage(),
            }
        return json.dumps(payload, default=str, separators=(",", ":"))


class ObservabilityContext:
    """Request-scoped telemetry accumulator.

    The context is intentionally independent from AgentState. This prevents
    telemetry concerns from changing agent business logic while still allowing
    the final summary to be attached to AgentState at the graph boundary.
    """

    def __init__(
        self,
        trace_id: str,
        conversation_id: str | None = None,
    ):
        self.trace_id = trace_id
        self.conversation_id = conversation_id
        self.started_at = time.perf_counter()
        self.llm_calls: list[LLMCallObservation] = []
        self._llm_started: dict[str, tuple[float, str | None]] = {}
        self._lock = Lock()
        self.stages: list[StageObservation] = []


    @contextmanager
    def stage(self, stage: str) -> Iterator[None]:
        """Capture one graph-node execution and associate nested LLM calls with it."""
        token = _CURRENT_STAGE.set(stage)
        started = time.perf_counter()
        status = "success"

        try:
            yield
        except BaseException as exc:
            status = (
                "interrupted"
                if type(exc).__name__ == "GraphInterrupt"
                else "failed"
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000

            with self._lock:
                calls = [
                    call
                    for call in self.llm_calls
                    if call.stage == stage
                ]

                self.stages.append(
                    StageObservation(
                        stage=stage,
                        duration_ms=duration_ms,
                        status=status,
                        llm_calls=len(calls),
                        input_tokens=sum(
                            c.input_tokens for c in calls
                        ),
                        output_tokens=sum(
                            c.output_tokens for c in calls
                        ),
                        total_tokens=sum(
                            c.total_tokens for c in calls
                        ),
                        estimated_cost=sum(
                            c.estimated_cost for c in calls
                        ),
                    )
                )

            _CURRENT_STAGE.reset(token)

    def start_llm(self, run_id: str, model: str | None = None) -> None:
        with self._lock:
            self._llm_started[str(run_id)] = (time.perf_counter(), model)

    def record_llm(
        self,
        *,
        run_id: str,
        model: str | None,
        provider: str | None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        success: bool = True,
        error_type: str | None = None,
    ) -> None:
        with self._lock:
            started_info = self._llm_started.pop(str(run_id), None)

        started = started_info[0] if started_info else None
        started_model = started_info[1] if started_info else None

        duration_ms = (
            (time.perf_counter() - started) * 1000
            if started is not None
            else 0.0
        )

        if model is None:
            model = started_model

        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens

        input_rate = _env_float("OBSERVABILITY_INPUT_COST_PER_1M")
        output_rate = _env_float("OBSERVABILITY_OUTPUT_COST_PER_1M")

        estimated_cost = (
            input_tokens / 1_000_000 * input_rate
            + output_tokens / 1_000_000 * output_rate
        )

        observation = LLMCallObservation(
            model=model,
            provider=provider,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            stage=_CURRENT_STAGE.get(),
            success=success,
            error_type=error_type,
        )

        with self._lock:
            self.llm_calls.append(observation)

        _LOGGER.info(
            "llm_call",
            extra={
                "observability_payload": {
                    "event": "llm_call",
                    "trace_id": self.trace_id,
                    "conversation_id": self.conversation_id,
                    **observation.model_dump(),
                }
            },
        )

    def _build_model_observations(self) -> list[ModelObservation]:
        """Aggregate LLM observations by provider and model."""

        aggregates: dict[tuple[str | None, str | None], ModelObservation] = {}

        for call in self.llm_calls:
            key = (call.provider, call.model)

            if key not in aggregates:
                aggregates[key] = ModelObservation(
                    provider=call.provider,
                    model=call.model,
                )

            aggregate = aggregates[key]

            aggregate.calls += 1

            if call.success:
                aggregate.successful_calls += 1
            else:
                aggregate.failed_calls += 1

            aggregate.total_duration_ms += call.duration_ms
            aggregate.input_tokens += call.input_tokens
            aggregate.output_tokens += call.output_tokens
            aggregate.total_tokens += call.total_tokens
            aggregate.estimated_cost = round(
                aggregate.estimated_cost + call.estimated_cost,
                10,
            )

        return list(aggregates.values())

    def summary(
        self,
        execution_trace: list[dict[str, object]] | None = None,
    ) -> ObservabilitySummary:
        trace = execution_trace or []

        total_duration_ms = (time.perf_counter() - self.started_at) * 1000
        failures = sum(1 for event in trace if event.get("status") == "failed")
        retries = sum(
            1
            for event in trace
            if isinstance(event.get("attempt"), int)
            and event.get("attempt", 0) > 1
        )

        input_tokens = sum(item.input_tokens for item in self.llm_calls)
        output_tokens = sum(item.output_tokens for item in self.llm_calls)
        total_tokens = sum(item.total_tokens for item in self.llm_calls)
        cost = sum(item.estimated_cost for item in self.llm_calls)
        models = self._build_model_observations()

        result = ObservabilitySummary(
            trace_id=self.trace_id,
            conversation_id=self.conversation_id,
            total_duration_ms=total_duration_ms,
            model_calls=len(self.llm_calls),
            successful_model_calls=sum(
                1 for item in self.llm_calls if item.success
            ),
            failed_model_calls=sum(
                1 for item in self.llm_calls if not item.success
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            retry_count=retries,
            failure_count=failures,
            execution_events=len(trace),
            llm_calls=list(self.llm_calls),
            models=models,
            stages=self.stages,

            metadata={
                "cost_tracking_enabled": bool(
                    _env_float("OBSERVABILITY_INPUT_COST_PER_1M")
                    or _env_float("OBSERVABILITY_OUTPUT_COST_PER_1M")
                ),
            },
        )

        _LOGGER.info(
            "agent_execution",
            extra={
                "observability_payload": {
                    "event": "agent_execution",
                    **result.model_dump(),
                }
            },
        )

        return result


class ObservabilityCallbackHandler(BaseCallbackHandler):
    """LangChain callback that records model latency and token usage."""

    def _context(self) -> ObservabilityContext | None:
        return _CURRENT_CONTEXT.get()

    @staticmethod
    def _model_name(serialized: dict[str, Any] | None) -> str | None:
        serialized = serialized or {}
        kwargs = serialized.get("kwargs", {})
        return (
            kwargs.get("model")
            or kwargs.get("model_name")
            or serialized.get("name")
        )

    @staticmethod
    def _token_usage(response: Any) -> tuple[int, int, int]:
        usage: dict[str, Any] = {}

        llm_output = getattr(response, "llm_output", None)
        if isinstance(llm_output, dict):
            candidate = llm_output.get("token_usage")
            if isinstance(candidate, dict):
                usage = candidate

        if not usage:
            generations = getattr(response, "generations", None) or []
            if generations and generations[0]:
                message = getattr(generations[0][0], "message", None)
                message_usage = getattr(message, "usage_metadata", None)
                if isinstance(message_usage, dict):
                    usage = message_usage

        input_tokens = int(
            usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
        )
        output_tokens = int(
            usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
        )
        total_tokens = int(
            usage.get("total_tokens", input_tokens + output_tokens) or 0
        )

        return input_tokens, output_tokens, total_tokens

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        context = self._context()
        if context is not None:
            context.start_llm(str(run_id), self._model_name(serialized))

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        context = self._context()
        if context is not None:
            context.start_llm(str(run_id), self._model_name(serialized))

    def on_llm_end(
        self,
        response: Any,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        context = self._context()
        if context is None:
            return

        input_tokens, output_tokens, total_tokens = self._token_usage(response)
        context.record_llm(
            run_id=str(run_id),
            model=kwargs.get("model"),
            provider="langchain",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            success=True,
        )

    def on_llm_error(
        self,
        error: BaseException,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        context = self._context()
        if context is None:
            return

        context.record_llm(
            run_id=str(run_id),
            model=kwargs.get("model"),
            provider="langchain",
            success=False,
            error_type=type(error).__name__,
        )


class ObservabilityService:
    """Creates request-scoped observability contexts."""

    def __init__(self):
        self.callback_handler = ObservabilityCallbackHandler()
        self._configure_logger()

    @staticmethod
    def _configure_logger() -> None:
        if getattr(_LOGGER, "_datapilot_configured", False):
            return

        handler = logging.StreamHandler()
        handler.setFormatter(JsonObservabilityFormatter())
        _LOGGER.addHandler(handler)
        _LOGGER.setLevel(
            getattr(
                logging,
                os.getenv("OBSERVABILITY_LOG_LEVEL", "INFO").upper(),
                logging.INFO,
            )
        )
        _LOGGER.propagate = False
        _LOGGER._datapilot_configured = True

    @contextmanager
    def capture(
        self,
        *,
        conversation_id: str | None = None,
        trace_id: str | None = None,
    ) -> Iterator[ObservabilityContext]:
        context = ObservabilityContext(
            trace_id=trace_id or str(uuid.uuid4()),
            conversation_id=conversation_id,
        )
        token = _CURRENT_CONTEXT.set(context)

        try:
            yield context
        except Exception:
            _CURRENT_CONTEXT.reset(token)
            raise
        else:
            _CURRENT_CONTEXT.reset(token)
