from typing import Any

from pydantic import BaseModel, Field


class MetadataResult(BaseModel):

    schemas: list[dict[str, Any]]

    schema_text: str

    metadata: str


class SQLResult(BaseModel):

    success: bool

    sql: str | None = None

    attempts: int = 0

    errors: list[str] = Field(
        default_factory=list
    )


class AnalyticsResult(BaseModel):

    success: bool

    execution: dict[str, Any] | None = None

    analysis: dict[str, Any] | None = None

    error: str | None = None