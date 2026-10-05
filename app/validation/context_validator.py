import sqlglot
from sqlglot import exp

from models.context_validation import ContextValidationResult
from models.sql_requirements import SQLRequirements


class ContextValidator:
    """
    Validates generated SQL against deterministic SQLRequirements.

    This validator checks analytical intent rather than only SQL syntax.

    Validation includes:
        - LIMIT
        - ORDER BY direction
        - GROUP BY
        - required time range
        - required filters
        - schema-aware columns

    The validator does not generate or modify SQL.
    It only determines whether the generated SQL satisfies
    the analytical requirements.
    """

    def validate(
        self,
        sql: str,
        requirements: SQLRequirements,
        schemas: list[dict] | None = None,
    ) -> ContextValidationResult:

        errors: list[str] = []
        warnings: list[str] = []

        if not sql or not sql.strip():
            return ContextValidationResult(
                is_valid=False,
                errors=["Generated SQL is empty."]
            )

        try:
            expression = sqlglot.parse_one(
                sql,
                dialect="postgres"
            )
        except Exception as exc:
            return ContextValidationResult(
                is_valid=False,
                errors=[
                    f"Unable to parse generated SQL: {str(exc)}"
                ]
            )

        schema_map = self._build_schema_map(schemas)

        errors.extend(
            self._validate_limit(
                expression,
                requirements
            )
        )

        errors.extend(
            self._validate_ordering(
                expression,
                requirements
            )
        )

        errors.extend(
            self._validate_grouping(
                expression,
                requirements,
                schema_map
            )
        )

        errors.extend(
            self._validate_time_range(
                expression,
                requirements
            )
        )

        errors.extend(
            self._validate_filters(
                expression,
                requirements,
                schema_map
            )
        )

        return ContextValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ============================================================
    # SCHEMA
    # ============================================================

    @staticmethod
    def _build_schema_map(
        schemas: list[dict] | None
    ) -> dict[str, set[str]]:

        """
        Convert database schema information into:

            {
                "products": {"id", "name", "price"},
                "orders": {"id", "customer_id", "order_date"},
            }

        The validator intentionally supports both common schema
        representations:

            {
                "table": "products",
                "columns": [
                    {"name": "id"},
                    {"name": "name"}
                ]
            }

        and:

            {
                "table": "products",
                "columns": ["id", "name"]
            }
        """

        if not schemas:
            return {}

        schema_map: dict[str, set[str]] = {}

        for schema in schemas:

            if not isinstance(schema, dict):
                continue

            table_name = schema.get("table")

            if not table_name:
                continue

            columns = schema.get("columns", [])

            column_names: set[str] = set()

            for column in columns:

                if isinstance(column, str):
                    column_names.add(column.lower())

                elif isinstance(column, dict):
                    column_name = column.get("name")

                    if column_name:
                        column_names.add(
                            str(column_name).lower()
                        )

            schema_map[str(table_name).lower()] = column_names

        return schema_map

    # ============================================================
    # LIMIT
    # ============================================================

    def _validate_limit(
        self,
        expression,
        requirements: SQLRequirements,
    ) -> list[str]:

        if requirements.limit is None:
            return []

        limit_expression = expression.args.get("limit")

        if limit_expression is None:
            return [
                f"Expected LIMIT {requirements.limit}, "
                "but no LIMIT clause was found."
            ]

        limit_value = self._extract_limit_value(
            limit_expression
        )

        if limit_value is None:
            return [
                "Unable to determine the generated SQL LIMIT value."
            ]

        if limit_value != requirements.limit:
            return [
                f"Expected LIMIT {requirements.limit} "
                f"but found LIMIT {limit_value}."
            ]

        return []

    def _extract_limit_value(
        self,
        limit_expression
    ) -> int | None:

        expression = limit_expression.expression

        if isinstance(expression, exp.Literal):
            try:
                return int(expression.this)
            except (TypeError, ValueError):
                return None

        return None

    # ============================================================
    # ORDERING
    # ============================================================

    def _validate_ordering(
        self,
        expression,
        requirements: SQLRequirements,
    ) -> list[str]:

        if requirements.sort_direction is None:
            return []

        order_expression = expression.args.get("order")

        if order_expression is None:
            return [
                "A sort direction was requested, "
                "but no ORDER BY clause was found."
            ]

        expected_direction = self._normalize_sort_direction(
            requirements.sort_direction
        )

        if expected_direction is None:
            return [
                f"Unsupported sort direction "
                f"'{requirements.sort_direction}'."
            ]

        ordered_expressions = order_expression.expressions

        if not ordered_expressions:
            return [
                "ORDER BY clause does not contain an expression."
            ]

        primary_order = ordered_expressions[0]

        actual_direction = "ASC"

        if isinstance(primary_order, exp.Ordered):

            if primary_order.args.get("desc"):
                actual_direction = "DESC"

        if actual_direction != expected_direction:

            return [
                f"Expected {expected_direction} ordering "
                f"but found {actual_direction}."
            ]

        return []


    @staticmethod
    def _normalize_sort_direction(
        sort_direction: str
    ) -> str | None:

        direction = sort_direction.strip().lower()

        if direction in {"asc", "ascending"}:
            return "ASC"

        if direction in {"desc", "descending"}:
            return "DESC"

        return None

    # ============================================================
    # GROUPING
    # ============================================================

    def _validate_grouping(
        self,
        expression,
        requirements: SQLRequirements,
        schema_map: dict[str, set[str]],
    ) -> list[str]:

        if not requirements.group_by_required:
            return []

        group_expression = expression.args.get("group")

        if group_expression is None:
            return [
                "Analytical context requires entity-level grouping, "
                "but no GROUP BY clause was found."
            ]

        if not group_expression.expressions:
            return [
                "GROUP BY clause is empty."
            ]

        errors: list[str] = []

        if not schema_map:
            return errors

        for group_item in group_expression.expressions:

            column = self._extract_column(group_item)

            if column is None:
                continue

            if not self._column_exists_in_schema(
                column,
                schema_map
            ):
                errors.append(
                    f"GROUP BY column '{column.name}' "
                    "was not found in the database schema."
                )

        return errors

    # ============================================================
    # TIME RANGE
    # ============================================================

    def _validate_time_range(
        self,
        expression,
        requirements: SQLRequirements,
    ) -> list[str]:

        if not requirements.time_range_required:
            return []

        time_range = requirements.time_range

        if not time_range:
            return []

        start = time_range.get("start")
        end = time_range.get("end")

        if not start or not end:
            return [
                "Time-range requirement is missing start or end date."
            ]

        literals = []

        for literal in expression.find_all(exp.Literal):

            if not literal.is_string:
                continue

            value = str(literal.this)

            if self._looks_like_date(value):
                literals.append(value)

        if not literals:
            return [
                f"Expected SQL to contain the required time range "
                f"{start} to {end}, but no date literals were found."
            ]

        return []

    # ============================================================
    # FILTERS
    # ============================================================

    def _validate_filters(
        self,
        expression,
        requirements: SQLRequirements,
        schema_map: dict[str, set[str]],
    ) -> list[str]:

        if not requirements.filters:
            return []

        errors: list[str] = []

        for filter_requirement in requirements.filters:

            field = filter_requirement.get("field")

            if not field:
                continue

            field = str(field).lower()

            matching_columns = []

            for column in expression.find_all(exp.Column):

                if column.name.lower() == field:
                    matching_columns.append(column)

            if not matching_columns:
                errors.append(
                    f"Required filter field '{field}' "
                    "was not found in generated SQL."
                )
                continue

            # If schema information is available, make sure
            # the requested filter field actually exists.
            if schema_map:

                if not self._column_exists_in_schema_name(
                    field,
                    schema_map
                ):
                    errors.append(
                        f"Required filter field '{field}' "
                        "does not exist in the database schema."
                    )
                    continue

            # The field must actually participate in a predicate.
            if not self._column_used_in_predicate(
                expression,
                field
            ):
                errors.append(
                    f"Required filter field '{field}' "
                    "was referenced but is not used in a filter predicate."
                )

        return errors

    # ============================================================
    # FILTER HELPERS
    # ============================================================

    def _column_used_in_predicate(
        self,
        expression,
        field: str
    ) -> bool:

        """
        Check whether the required column participates in a
        WHERE/HAVING predicate.

        Example that passes:

            WHERE city = 'Delhi'

        Example that fails:

            SELECT city
            FROM customers

        because merely selecting the column does not mean
        the requested filter was applied.
        """

        where_expression = expression.args.get("where")

        if where_expression is not None:

            for column in where_expression.find_all(exp.Column):

                if column.name.lower() == field.lower():
                    return True

        having_expression = expression.args.get("having")

        if having_expression is not None:

            for column in having_expression.find_all(exp.Column):

                if column.name.lower() == field.lower():
                    return True

        return False

    # ============================================================
    # COLUMN / SCHEMA HELPERS
    # ============================================================

    @staticmethod
    def _extract_column(expression):

        if isinstance(expression, exp.Column):
            return expression

        if isinstance(expression, exp.Alias):
            inner = expression.this

            if isinstance(inner, exp.Column):
                return inner

        return None

    @staticmethod
    def _column_exists_in_schema_name(
        column_name: str,
        schema_map: dict[str, set[str]]
    ) -> bool:

        column_name = column_name.lower()

        return any(
            column_name in columns
            for columns in schema_map.values()
        )

    @staticmethod
    def _column_exists_in_schema(
        column: exp.Column,
        schema_map: dict[str, set[str]]
    ) -> bool:

        column_name = column.name.lower()

        # If SQL contains a table qualifier:
        #
        # products.name
        #
        # validate against that table specifically.

        table_name = column.table

        if table_name:

            table_name = table_name.lower()

            if table_name in schema_map:
                return column_name in schema_map[table_name]

        # For unqualified columns, search all known tables.
        return any(
            column_name in columns
            for columns in schema_map.values()
        )

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _looks_like_date(value: str) -> bool:

        if len(value) != 10:
            return False

        return (
            value[4] == "-"
            and value[7] == "-"
            and value[:4].isdigit()
            and value[5:7].isdigit()
            and value[8:10].isdigit()
        )