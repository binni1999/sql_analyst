from dataclasses import dataclass, field


@dataclass(frozen=True)
class SQLSecurityPolicy:
    """Configurable security policy for SQL execution."""

    allowed_tables: frozenset[str] | None = None
    allowed_columns: dict[str, frozenset[str]] = field(default_factory=dict)

    max_joins: int = 5
    max_subqueries: int = 5
    max_query_length: int = 10_000

    require_limit_for_wildcard: bool = True
    require_limit_for_large_result: bool = True
    max_result_rows: int = 1_000
    query_timeout_ms: int = 10_000

    allow_cte: bool = True
    allow_subqueries: bool = True

    sensitive_columns: dict[str, frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_query_length <= 0:
            raise ValueError("max_query_length must be greater than zero")
        if self.max_joins < 0:
            raise ValueError("max_joins cannot be negative")
        if self.max_subqueries < 0:
            raise ValueError("max_subqueries cannot be negative")
        if self.max_result_rows <= 0:
            raise ValueError("max_result_rows must be greater than zero")
        if self.query_timeout_ms <= 0:
            raise ValueError("query_timeout_ms must be greater than zero")

    @staticmethod
    def _normalize_names(values):
        return frozenset(str(value).lower() for value in values)

    def normalized_allowed_tables(self) -> frozenset[str] | None:
        if self.allowed_tables is None:
            return None
        return self._normalize_names(self.allowed_tables)

    def normalized_allowed_columns(self) -> dict[str, frozenset[str]]:
        return {
            table.lower(): self._normalize_names(columns)
            for table, columns in self.allowed_columns.items()
        }

    def normalized_sensitive_columns(self) -> dict[str, frozenset[str]]:
        return {
            table.lower(): self._normalize_names(columns)
            for table, columns in self.sensitive_columns.items()
        }
