from typing import Any

from pydantic import BaseModel, Field


class AnalyticalContext(BaseModel):
    entity: str | None = None

    metric: str | None = None

    aggregation: str | None = None

    limit: int | None = None

    sort_direction: str | None = None

    filters: list[dict[str, Any]] = Field(
        default_factory=list
    )

    time_range: dict[str, Any] | None = None