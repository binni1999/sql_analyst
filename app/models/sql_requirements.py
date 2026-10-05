from typing import Any

from pydantic import BaseModel, Field


class SQLRequirements(BaseModel):
    """
    Deterministic SQL requirements derived from AnalyticalContext.
    """

    metric: str | None = None

    aggregation: str | None = None

    entity: str | None = None

    group_by_required: bool = False

    filters: list[dict[str, Any]] = Field(default_factory=list)

    time_range: dict[str, Any] | None = None

    time_range_required: bool = False

    sort_direction: str | None = None

    limit: int | None = None