from models.sql_error import SQLError, SQLErrorType
from models.analytical_context import AnalyticalContext
from models.sql_error import SQLError, SQLErrorType
from models.sql_requirements import SQLRequirements


class SQLRepairStrategy:
    """
    Builds targeted repair instructions based on the type of
    SQL validation error.

    This class does not generate or modify SQL.
    It only produces instructions that can later be supplied
    to the SQL generation/repair component.
    """

    def build_instruction(
        self,
        error: SQLError,
        analytical_context: AnalyticalContext | None = None,
        requirements: SQLRequirements | None = None,
    ) -> str:

        if error.error_type == SQLErrorType.SYNTAX:
            return self._syntax_instruction(error)

        if error.error_type == SQLErrorType.DATABASE:
            return self._database_instruction(error)

        if error.error_type == SQLErrorType.SEMANTIC:
            return self._semantic_instruction(
                error,
                analytical_context,
                requirements,
            )

        if error.error_type == SQLErrorType.CONTEXT:
            return self._context_instruction(
                error,
                analytical_context,
                requirements,
            )

        return self._generic_instruction(error)
        
    def build_instructions(
        self,
        errors: list[SQLError],
        analytical_context: AnalyticalContext | None = None,
        requirements: SQLRequirements | None = None,
    ) -> list[str]:
        return [
            self.build_instruction(
                error,
                analytical_context=analytical_context,
                requirements=requirements,
            )
            for error in errors
        ]

    def _build_context_text(
        self,
        analytical_context: AnalyticalContext | None,
        requirements: SQLRequirements | None,
    ) -> str:

        sections = []

        if analytical_context is not None:
            sections.append(
                "ANALYTICAL CONTEXT:\n"
                f"{analytical_context.model_dump_json(indent=2)}"
            )

        if requirements is not None:
            sections.append(
                "SQL REQUIREMENTS:\n"
                f"{requirements.model_dump_json(indent=2)}"
            )

        if not sections:
            return (
                "No structured analytical context or SQL "
                "requirements are available."
            )

        return "\n\n".join(sections)

    def _syntax_instruction(
        self,
        error: SQLError,
    ) -> str:
        return (
            "SQL SYNTAX REPAIR:\n"
            "Fix the SQL syntax error without changing the "
            "user's analytical intent.\n"
            f"Error: {error.message}"
        )

    def _database_instruction(
        self,
        error: SQLError,
    ) -> str:
        return (
            "DATABASE COMPATIBILITY REPAIR:\n"
            "Fix the SQL so that it is valid for the provided "
            "database schema and PostgreSQL dialect.\n"
            "Verify table names, column names, joins, data types, "
            "and PostgreSQL-compatible expressions.\n"
            f"Error: {error.message}"
        )

    def _semantic_instruction(
        self,
        error: SQLError,
        analytical_context: AnalyticalContext | None = None,
        requirements: SQLRequirements | None = None,
    ) -> str:

        context_text = self._build_context_text(
            analytical_context,
            requirements,
        )

        return (
        "SEMANTIC REPAIR:\n"
        "Fix the SQL so that the requested business metric "
        "and its defined formula are preserved exactly.\n"
        "Do not substitute a different metric or aggregation "
        "unless explicitly requested by the user.\n\n"
        f"VALIDATION ERROR:\n"
        f"{error.message}\n\n"
        f"{context_text}"
    )

    def _context_instruction(
        self,
        error: SQLError,
        analytical_context: AnalyticalContext | None = None,
        requirements: SQLRequirements | None = None,
    ) -> str:

        context_text = self._build_context_text(
            analytical_context,
            requirements,
        )

        return (
        "ANALYTICAL CONTEXT REPAIR:\n"
        "Fix the SQL so that all requested analytical "
        "requirements are satisfied.\n\n"
        "Do not change the user's analytical intent.\n"
        "Preserve the requested entity, metric, aggregation, "
        "filters, time range, limit, and sort direction.\n\n"
        f"VALIDATION ERROR:\n"
        f"{error.message}\n\n"
        f"{context_text}"
        )

    def _generic_instruction(
        self,
        error: SQLError,
    ) -> str:
        return (
            "SQL REPAIR:\n"
            "Fix the reported SQL validation error while "
            "preserving the user's analytical intent.\n"
            f"Error: {error.message}"
        )