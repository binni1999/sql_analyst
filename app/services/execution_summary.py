from models.execution_summary import ExecutionTraceSummary


class ExecutionSummaryService:

    VALIDATION_STAGES = {
        "sqlglot_validation",
        "database_validation",
        "semantic_validation",
        "context_validation",
    }

    @staticmethod
    def build(
        execution_trace: list[dict[str, object]],
        successful: bool,
    ) -> ExecutionTraceSummary:

        total_duration_ms = sum(
            float(event.get("duration_ms", 0) or 0)
            for event in execution_trace
        )

        validation_failures = sum(
            1
            for event in execution_trace
            if (
                event.get("status") == "failed"
                and event.get("stage") in ExecutionSummaryService.VALIDATION_STAGES
            )
        )

        repairs = sum(
            1
            for event in execution_trace
            if event.get("stage") == "repair"
        )

        retry_count = sum(
            1
            for event in execution_trace
            if (
                isinstance(event.get("attempt"), int)
                and event.get("attempt", 0) > 1
            )
        )

        return ExecutionTraceSummary(
            total_events=len(execution_trace),
            total_duration_ms=total_duration_ms,
            retry_count=retry_count,
            validation_failures=validation_failures,
            repairs=repairs,
            successful=successful,
        )