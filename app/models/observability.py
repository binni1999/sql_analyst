
from typing import Any

from pydantic import BaseModel, Field


class StageObservation(BaseModel):
    """Aggregated telemetry for one graph/agent stage."""

    stage: str
    duration_ms: float = 0.0
    status: str = "success"
    execution_count: int = 1
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class LLMCallObservation(BaseModel):
    """Telemetry captured for one LLM invocation."""

    stage: str | None = None
    model: str | None = None
    provider: str | None = None
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    success: bool = True
    error_type: str | None = None

class ModelObservation(BaseModel):
    """Aggregated telemetry for one model/provider combination."""

    provider: str | None = None
    model: str | None = None
    calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    retry_count: int = 0
    total_duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class ObservabilitySummary(BaseModel):
    """Production-facing telemetry summary for one agent execution."""

    trace_id: str
    conversation_id: str | None = None
    total_duration_ms: float = 0.0
    model_calls: int = 0
    successful_model_calls: int = 0
    failed_model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    retry_count: int = 0
    failure_count: int = 0
    execution_events: int = 0
    llm_calls: list[LLMCallObservation] = Field(default_factory=list)
    models: list[ModelObservation] = Field(default_factory=list)
    stages: list[StageObservation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)