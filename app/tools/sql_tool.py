"""Structured SQL tools and an opt-in LangChain tool-call runner.

This module provides the Step 58 tool-calling foundation without changing
the existing SQLAgent or LangGraph workflow. Applications can bind the tools
to a chat model and use :class:`ToolCallingExecutor` independently.
"""

from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool

from models.analytical_context import AnalyticalContext
from models.business_knowledge import BusinessKnowledgeResult
from pydantic import BaseModel, Field


class GetSchemaInput(BaseModel):
    table_name: str | None = Field(
        default=None,
        description="Optional table name. Omit it to return the full schema.",
    )


class EmptyToolInput(BaseModel):
    """Input schema for tools that do not require arguments."""


class ValidateSQLInput(BaseModel):
    sql: str = Field(description="A read-only PostgreSQL SELECT query")


class ExecuteSQLInput(BaseModel):
    sql: str = Field(description="A read-only PostgreSQL SELECT query")


class RepairSQLInput(BaseModel):
    question: str = Field(description="The user's original analytics question")
    sql: str = Field(description="The SQL query to repair")
    errors: list[str] = Field(description="Validation errors to address")
    analytical_context: dict[str, Any] | None = Field(
        default=None,
        description="Structured analytical context that must be preserved during repair.",
    )
    business_knowledge: dict[str, Any] | None = Field(
        default=None,
        description="Retrieved business knowledge that must be respected during SQL repair.",
    )


class ToolCallError(Exception):
    """Raised when a named tool cannot be found or keeps failing."""


class ToolCallingExecutor:
    """Select, execute, and return model-requested tools with bounded retry.

    ``run`` performs normal LangChain tool calling: the model selects tools,
    this executor invokes them, and tool results are returned to the model
    until it responds without further tool calls or the round limit is hit.
    Individual tool invocations are retried on exceptions.
    """

    def __init__(
        self,
        tools: list[StructuredTool],
        *,
        max_retries: int = 1,
        max_tool_rounds: int = 5,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be at least 1")
        self.tools = list(tools)
        self.max_retries = max_retries
        self.max_tool_rounds = max_tool_rounds
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        if len(self._tools_by_name) != len(self.tools):
            raise ValueError("Tool names must be unique")

    def _record(
        self,
        trace: list[dict[str, Any]] | None,
        *,
        name: str,
        status: str,
        attempt: int,
        message: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        if trace is None:
            return
        event: dict[str, Any] = {
            "stage": "tool_call",
            "status": status,
            "attempt": attempt,
            "message": message or "",
            "metadata": {"tool": name},
        }
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        trace.append(event)

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        execution_trace: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Execute one named tool and retry exceptions up to ``max_retries``."""
        tool = self._tools_by_name.get(name)
        if tool is None:
            error = f"Unknown tool: {name}"
            self._record(
                execution_trace, name=name, status="failed", attempt=0,
                message=error,
            )
            raise ToolCallError(error)

        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            try:
                result = tool.invoke(arguments)
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._record(
                    execution_trace,
                    name=name,
                    status="failed" if attempt > self.max_retries else "retrying",
                    attempt=attempt,
                    message=f"{type(exc).__name__}: {exc}",
                    duration_ms=duration_ms,
                )
                if attempt > self.max_retries:
                    raise ToolCallError(
                        f"Tool {name!r} failed after {attempt} attempt(s): {exc}"
                    ) from exc
                continue

            self._record(
                execution_trace,
                name=name,
                status="success",
                attempt=attempt,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            return result

        raise AssertionError("unreachable")

    def run(
        self,
        model: Any,
        messages: list[Any],
        *,
        execution_trace: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Let a model select tools, execute its calls, and continue the turn."""
        bound_model = model.bind_tools(self.tools)
        conversation = list(messages)

        for _ in range(self.max_tool_rounds):
            response = bound_model.invoke(conversation)
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                return response

            conversation.append(response)
            for call in tool_calls:
                name = call.get("name", "")
                call_id = call.get("id", "")
                arguments = call.get("args", {})
                try:
                    result = self.execute(
                        name,
                        arguments,
                        execution_trace=execution_trace,
                    )
                    content = json.dumps(result, default=str)
                except ToolCallError as exc:
                    content = json.dumps({"success": False, "error": str(exc)})
                conversation.append(
                    ToolMessage(content=content, tool_call_id=call_id)
                )

        raise ToolCallError(
            f"Tool calling exceeded {self.max_tool_rounds} model round(s)"
        )


def build_sql_tools(
    *,
    db: Any,
    metadata_service: Any,
    sql_validator: Any,
    sql_generator: Any,
    secure_executor: Any = None,
) -> list[StructuredTool]:
    """Build the five SQL/data tools using the application's existing services.

    ``execute_sql`` requires the application's secure execution boundary.
    There is intentionally no raw ``db.execute_query`` fallback: this keeps
    model-selected tool calls from bypassing Step 67 security controls.
    """

    if secure_executor is None:
        raise ValueError(
            "secure_executor is required to build SQL execution tools."
        )

    def get_schema(table_name: str | None = None) -> Any:
        if table_name:
            return db.get_schema(table_name)
        return db.get_full_schema()

    def get_metadata() -> dict[str, Any]:
        return {
            "columns": metadata_service.get_column_metadata(),
            "metrics": metadata_service.get_metric_metadata(),
            "text": metadata_service.build_metadata_text(),
        }

    def validate_sql(sql: str) -> dict[str, Any]:
        schemas = db.get_full_schema()
        result = sql_validator.validate(sql, schemas)
        syntax_valid = bool(result.is_valid)
        database_result = db.validate_with_database(sql)
        database_valid = bool(database_result.get("valid"))
        return {
            "is_valid": syntax_valid and database_valid,
            "syntax_valid": syntax_valid,
            "database_valid": database_valid,
            "errors": [
                *list(getattr(result, "errors", [])),
                *([] if database_valid else [database_result.get("error") or "Database validation failed."]),
            ],
            "warnings": list(getattr(result, "warnings", [])),
        }

    def execute_sql(sql: str) -> dict[str, Any]:
        result = secure_executor.execute(sql)
        return {"success": True, **result}

    def repair_sql(
        question: str,
        sql: str,
        errors: list[str],
        analytical_context: dict[str, Any] | None = None,
        business_knowledge: dict[str, Any] | None = None,
    ) -> str:
        schemas = db.get_full_schema()
        schema_text = "\n".join(
            f"{item['table']}: " + ", ".join(
                f"{column['name']} {column['type']}"
                for column in item.get("columns", [])
            )
            for item in schemas
        )
        context = (
            AnalyticalContext.model_validate(analytical_context)
            if analytical_context is not None
            else None
        )

        knowledge = (
            BusinessKnowledgeResult.model_validate(business_knowledge)
            if business_knowledge is not None
            else None
        )

        return sql_generator.fix_sql(
            question=question,
            sql=sql,
            errors=errors,
            schema=schema_text,
            metadata=metadata_service.build_metadata_text(),
            analytical_context=context,
            business_knowledge=knowledge,
        )

    return [
        StructuredTool.from_function(
            get_schema,
            name="get_schema",
            description="Retrieve one table's schema or the full database schema.",
            args_schema=GetSchemaInput,
        ),
        StructuredTool.from_function(
            get_metadata,
            name="get_metadata",
            description="Retrieve business metric and column definitions.",
            args_schema=EmptyToolInput,
        ),
        StructuredTool.from_function(
            validate_sql,
            name="validate_sql",
            description="Check SQL syntax, schema references, and PostgreSQL validity.",
            args_schema=ValidateSQLInput,
        ),
        StructuredTool.from_function(
            execute_sql,
            name="execute_sql",
            description="Run a read-only SELECT query and return rows and columns.",
            args_schema=ExecuteSQLInput,
        ),
        StructuredTool.from_function(
            repair_sql,
            name="repair_sql",
            description="Repair SQL using the existing SQL generation model and validation errors.",
            args_schema=RepairSQLInput,
        ),
    ]
