from pydantic import BaseModel


class ExecutionTraceSummary(BaseModel):
    total_events: int = 0
    total_duration_ms: float = 0.0
    retry_count: int = 0
    validation_failures: int = 0
    repairs: int = 0
    successful: bool = False