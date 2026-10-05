from models.sql_error import SQLError, SQLErrorType


class SQLErrorClassifier:
    """
    Converts validator-specific error messages into structured SQLError objects.

    This class does not modify or interpret SQL itself.
    It only adds a consistent error category and source to
    existing validation errors.
    """

    def classify_syntax(
        self,
        errors: list[str],
    ) -> list[SQLError]:
        return [
            SQLError(
                error_type=SQLErrorType.SYNTAX,
                message=error,
                source="SQLValidator",
            )
            for error in errors
        ]

    def classify_database(
        self,
        errors: list[str],
    ) -> list[SQLError]:
        return [
            SQLError(
                error_type=SQLErrorType.DATABASE,
                message=error,
                source="DatabaseValidator",
            )
            for error in errors
        ]

    def classify_semantic(
        self,
        errors: list[str],
    ) -> list[SQLError]:
        return [
            SQLError(
                error_type=SQLErrorType.SEMANTIC,
                message=error,
                source="SemanticValidator",
            )
            for error in errors
        ]

    def classify_context(
        self,
        errors: list[str],
    ) -> list[SQLError]:
        return [
            SQLError(
                error_type=SQLErrorType.CONTEXT,
                message=error,
                source="ContextValidator",
            )
            for error in errors
        ]

    def classify(
        self,
        *,
        syntax_errors: list[str] | None = None,
        database_errors: list[str] | None = None,
        semantic_errors: list[str] | None = None,
        context_errors: list[str] | None = None,
    ) -> list[SQLError]:
        """
        Classify errors from all SQL validation stages.

        The order is intentionally deterministic:
        syntax -> database -> semantic -> context.
        """

        syntax_errors = syntax_errors or []
        database_errors = database_errors or []
        semantic_errors = semantic_errors or []
        context_errors = context_errors or []

        classified_errors: list[SQLError] = []

        classified_errors.extend(
            self.classify_syntax(syntax_errors)
        )

        classified_errors.extend(
            self.classify_database(database_errors)
        )

        classified_errors.extend(
            self.classify_semantic(semantic_errors)
        )

        classified_errors.extend(
            self.classify_context(context_errors)
        )

        return classified_errors