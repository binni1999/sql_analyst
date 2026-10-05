
import json
import logging
import os
from uuid import uuid4

from models.observability import ObservabilitySummary
from services.observability import (
    ObservabilityContext,
    JsonObservabilityFormatter,
)


def test_observability_context_records_llm_usage(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_INPUT_COST_PER_1M", "1")
    monkeypatch.setenv("OBSERVABILITY_OUTPUT_COST_PER_1M", "2")

    context = ObservabilityContext(
        trace_id="trace-1",
        conversation_id="conversation-1",
    )
    run_id = str(uuid4())
    context.start_llm(run_id, model="test-model")
    context.record_llm(
        run_id=run_id,
        model=None,
        provider="test",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
    )

    summary = context.summary(
        [
            {"stage": "sql", "status": "success", "attempt": 0},
            {"stage": "repair", "status": "success", "attempt": 2},
            {"stage": "validation", "status": "failed", "attempt": 1},
        ]
    )

    assert summary.trace_id == "trace-1"
    assert summary.model_calls == 1
    assert summary.input_tokens == 1000
    assert summary.output_tokens == 500
    assert summary.total_tokens == 1500
    assert summary.retry_count == 1
    assert summary.failure_count == 1
    assert summary.estimated_cost == 0.002


def test_json_observability_formatter_outputs_valid_json():
    formatter = JsonObservabilityFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="ignored",
        args=(),
        exc_info=None,
    )
    record.observability_payload = {
        "event": "llm_call",
        "trace_id": "trace-1",
        "total_tokens": 123,
    }

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "llm_call"
    assert payload["trace_id"] == "trace-1"
    assert payload["total_tokens"] == 123


def test_observability_summary_is_pydantic_serializable():
    summary = ObservabilitySummary(
        trace_id="trace-1",
        model_calls=1,
        total_tokens=10,
    )

    payload = summary.model_dump()

    assert payload["trace_id"] == "trace-1"
    assert payload["model_calls"] == 1
    assert payload["total_tokens"] == 10


def test_observability_context_records_stage_metrics(monkeypatch):
    context = ObservabilityContext(
        trace_id="trace-stage",
        conversation_id="conversation-stage",
    )

    with context.stage("sql"):
        run_id = str(uuid4())
        context.start_llm(run_id, model="test-model")
        context.record_llm(
            run_id=run_id,
            model=None,
            provider="test",
            input_tokens=100,
            output_tokens=25,
            total_tokens=125,
        )

    summary = context.summary(
        [{"stage": "sql", "status": "success", "attempt": 1}]
    )

    assert len(summary.stages) == 1
    stage = summary.stages[0]
    assert stage.stage == "sql"
    assert stage.status == "success"
    assert stage.llm_calls == 1
    assert stage.input_tokens == 100
    assert stage.output_tokens == 25
    assert stage.total_tokens == 125
    assert stage.duration_ms >= 0
    assert summary.llm_calls[0].stage == "sql"


def test_observability_summary_aggregates_llm_calls_by_model(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_INPUT_COST_PER_1M", "1")
    monkeypatch.setenv("OBSERVABILITY_OUTPUT_COST_PER_1M", "2")

    context = ObservabilityContext(
        trace_id="trace-models",
        conversation_id="conversation-models",
    )

    first_run = str(uuid4())
    context.start_llm(first_run, model="model-a")
    context.record_llm(
        run_id=first_run,
        model=None,
        provider="provider-a",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )

    second_run = str(uuid4())
    context.start_llm(second_run, model="model-a")
    context.record_llm(
        run_id=second_run,
        model=None,
        provider="provider-a",
        input_tokens=200,
        output_tokens=100,
        total_tokens=300,
    )

    third_run = str(uuid4())
    context.start_llm(third_run, model="model-b")
    context.record_llm(
        run_id=third_run,
        model=None,
        provider="provider-b",
        input_tokens=50,
        output_tokens=25,
        total_tokens=75,
    )

    summary = context.summary()

    assert len(summary.models) == 2

    model_a = next(
        item
        for item in summary.models
        if item.provider == "provider-a"
        and item.model == "model-a"
    )

    assert model_a.calls == 2
    assert model_a.successful_calls == 2
    assert model_a.failed_calls == 0
    assert model_a.input_tokens == 300
    assert model_a.output_tokens == 150
    assert model_a.total_tokens == 450
    assert model_a.estimated_cost == 0.0006

    model_b = next(
        item
        for item in summary.models
        if item.provider == "provider-b"
        and item.model == "model-b"
    )

    assert model_b.calls == 1
    assert model_b.successful_calls == 1
    assert model_b.failed_calls == 0
    assert model_b.input_tokens == 50
    assert model_b.output_tokens == 25
    assert model_b.total_tokens == 75
    assert model_b.estimated_cost == 0.0001


def test_observability_model_aggregation_tracks_failed_calls():
    context = ObservabilityContext(
        trace_id="trace-model-failure",
        conversation_id="conversation-model-failure",
    )

    successful_run = str(uuid4())
    context.start_llm(successful_run, model="test-model")
    context.record_llm(
        run_id=successful_run,
        model=None,
        provider="test-provider",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        success=True,
    )

    failed_run = str(uuid4())
    context.start_llm(failed_run, model="test-model")
    context.record_llm(
        run_id=failed_run,
        model=None,
        provider="test-provider",
        success=False,
        error_type="TimeoutError",
    )

    summary = context.summary()

    assert len(summary.models) == 1

    model = summary.models[0]

    assert model.provider == "test-provider"
    assert model.model == "test-model"
    assert model.calls == 2
    assert model.successful_calls == 1
    assert model.failed_calls == 1

