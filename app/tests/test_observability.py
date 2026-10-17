
import json
import logging
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from types import SimpleNamespace

from services.observability import ObservabilityService
from models.observability import ObservabilitySummary
from services.observability import (
    ObservabilityContext,
    JsonObservabilityFormatter,
    ObservabilityService,
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


def test_capture_preserves_conversation_id():
    service = ObservabilityService()

    with service.capture(
        conversation_id="conversation-123",
        trace_id="trace-123",
    ) as context:
        assert context.trace_id == "trace-123"
        assert context.conversation_id == "conversation-123"

    summary = context.summary()

    assert summary.trace_id == "trace-123"
    assert summary.conversation_id == "conversation-123"






def test_callback_records_llm_token_usage():


    service = ObservabilityService()
    handler = service.callback_handler
    run_id = uuid4()

    with service.capture(
        conversation_id="token-telemetry-test"
    ) as context:
        handler.on_llm_start(
            serialized={
                "name": "fake-model",
                "kwargs": {"model": "fake-model"},
            },
            prompts=["A fake prompt"],
            run_id=run_id,
        )

        handler.on_llm_end(
            response=SimpleNamespace(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    }
                }
            ),
            run_id=run_id,
            model="fake-model",
        )

        assert len(context.llm_calls) == 1

        call = context.llm_calls[0]
        assert call.input_tokens == 10
        assert call.output_tokens == 5
        assert call.total_tokens == 15
        assert call.success is True

        summary = context.summary()

        assert summary.model_calls == 1
        assert summary.successful_model_calls == 1
        assert summary.failed_model_calls == 0

        assert summary.llm_calls[0].input_tokens == 10
        assert summary.llm_calls[0].output_tokens == 5
        assert summary.llm_calls[0].total_tokens == 15



def test_concurrent_requests_keep_observability_context_isolated():
    service = ObservabilityService()

    def run_request(conversation_id, stage_name):
        with service.capture(conversation_id=conversation_id) as context:
            with context.stage(stage_name):
                run_id = uuid4()

                service.callback_handler.on_llm_start(
                    serialized={
                        "name": "fake-model",
                        "kwargs": {"model": "fake-model"},
                    },
                    prompts=["Test prompt"],
                    run_id=run_id,
                )

                service.callback_handler.on_llm_end(
                    response=SimpleNamespace(
                        llm_output={
                            "token_usage": {
                                "prompt_tokens": 10,
                                "completion_tokens": 5,
                                "total_tokens": 15,
                            }
                        }
                    ),
                    run_id=run_id,
                    model="fake-model",
                )

            return context.summary()

    requests = [
        ("conversation-A", "sql_agent"),
        ("conversation-B", "answer_generation"),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        summaries = list(
            executor.map(
                lambda args: run_request(*args),
                requests,
            )
        )

    by_conversation = {
        summary.conversation_id: summary for summary in summaries
    }

    assert set(by_conversation) == {
        "conversation-A",
        "conversation-B",
    }

    sql_summary = by_conversation["conversation-A"]
    answer_summary = by_conversation["conversation-B"]

    assert len(sql_summary.llm_calls) == 1
    assert sql_summary.llm_calls[0].stage == "sql_agent"
    assert sql_summary.total_tokens == 15

    assert len(answer_summary.llm_calls) == 1
    assert answer_summary.llm_calls[0].stage == "answer_generation"
    assert answer_summary.total_tokens == 15

    assert len(sql_summary.stages) == 1
    assert sql_summary.stages[0].stage == "sql_agent"

    assert len(answer_summary.stages) == 1
    assert answer_summary.stages[0].stage == "answer_generation"



def test_observability_stage_records_failure_and_restores_context():
    from services.observability import _CURRENT_STAGE

    service = ObservabilityService()

    with service.capture(conversation_id="failed-stage-test") as context:
        assert _CURRENT_STAGE.get() is None

        try:
            with context.stage("sql_agent"):
                assert _CURRENT_STAGE.get() == "sql_agent"
                raise ValueError("Simulated SQL-agent failure")
        except ValueError:
            pass

        assert _CURRENT_STAGE.get() is None

    summary = context.summary()

    assert len(summary.stages) == 1
    assert summary.stages[0].stage == "sql_agent"
    assert summary.stages[0].status == "failed"


def test_observability_stage_records_graph_interruption():
    from services.observability import _CURRENT_STAGE

    class GraphInterrupt(Exception):
        pass

    service = ObservabilityService()

    with service.capture(conversation_id="interrupted-stage-test") as context:
        try:
            with context.stage("sql_agent"):
                raise GraphInterrupt("Simulated graph interruption")
        except GraphInterrupt:
            pass

        assert _CURRENT_STAGE.get() is None

    summary = context.summary()

    assert len(summary.stages) == 1
    assert summary.stages[0].stage == "sql_agent"
    assert summary.stages[0].status == "interrupted"
