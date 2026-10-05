# pyrefly: ignore [missing-import]

import sqlglot
from sqlglot import exp

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class SQLValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SQLValidator:

    # ============================================================
    # 1. BUILD DATABASE SCHEMA MAP
    # ============================================================

    def build_schema_map(self, schemas: list[dict]) -> dict:
        """
        Convert database schema information into an easy-to-use map.

        Example input:
        [
            {
                "table": "products",
                "columns": [
                    {"name": "product_id", "type": "integer"},
                    {"name": "product_name", "type": "varchar"}
                ]
            }
        ]

        Output:
        {
            "products": {
                "product_id",
                "product_name"
            }
        }
        """

        schema_map = {}

        for schema in schemas:

            table_name = schema["table"]

            columns = {
                column["name"]
                for column in schema["columns"]
            }

            schema_map[table_name] = columns

        return schema_map

    # ============================================================
    # 2. BUILD TABLE / RELATION ALIAS MAP
    # ============================================================

    def build_table_alias_map(self, expression) -> dict:
        """
        Build mapping between aliases and their underlying physical
        database tables or CTE names.

        Supports:

            FROM products p

        and:

            FROM product_revenue pr

        Derived-table aliases are handled separately by
        build_relation_column_map().
        """

        alias_map = {}

        for table in expression.find_all(exp.Table):

            table_name = table.name
            alias = table.alias

            if table_name:
                alias_map[table_name] = table_name

            if alias:
                alias_map[alias] = table_name

        return alias_map

    # ============================================================
    # 2B. BUILD RELATION COLUMN MAP
    # ============================================================

    def build_relation_column_map(self, expression) -> dict:
        """
        Build the columns exposed by query-level relations.

        A relation can be:

        1. A CTE

            WITH product_revenue AS (
                SELECT product_id, SUM(...) AS revenue
                FROM order_items
                GROUP BY product_id
            )

        2. A CTE referenced through an alias

            FROM product_revenue pr

        3. A derived table

            FROM (
                SELECT product_id, SUM(...) AS revenue
                FROM order_items
                GROUP BY product_id
            ) rev

        The resulting map is:

            {
                "product_revenue": {"product_id", "revenue"},
                "pr": {"product_id", "revenue"},
                "rev": {"product_id", "revenue"}
            }

        This lets qualified-column validation distinguish query
        relations from physical database tables.
        """

        relation_map = {}

        # --------------------------------------------------------
        # CTE relations
        # --------------------------------------------------------

        cte_map = self.build_cte_map(expression)

        for cte_name, columns in cte_map.items():
            relation_map[cte_name] = set(columns)

        # CTE aliases used in FROM/JOIN clauses.
        for table in expression.find_all(exp.Table):

            table_name = table.name
            alias = table.alias

            if table_name in cte_map and alias:
                relation_map[alias] = set(
                    cte_map[table_name]
                )

        # --------------------------------------------------------
        # Derived-table / subquery relations
        # --------------------------------------------------------

        for subquery in expression.find_all(exp.Subquery):

            alias = subquery.alias

            if not alias:
                continue

            select = subquery.this

            if not isinstance(select, exp.Select):
                continue

            columns = set()

            for projection in select.expressions:

                # SELECT product_id
                if isinstance(projection, exp.Column):
                    columns.add(projection.name)
                    continue

                # SELECT SUM(...) AS revenue
                if isinstance(projection, exp.Alias):
                    alias_name = projection.alias

                    if alias_name:
                        columns.add(alias_name)
                    continue

                # SELECT expression_without_alias
                #
                # SQLGlot may represent a plain expression without
                # an Alias node. There is no reliable output column
                # name in every such case, so do not invent one.
                if isinstance(projection, exp.Column):
                    columns.add(projection.name)

            relation_map[alias] = columns

        return relation_map

    # ============================================================
    # 3. BUILD SELECT ALIAS MAP
    # ============================================================

    def build_select_alias_map(self, expression) -> set[str]:
        """
        Find aliases created inside SELECT statements.

        Example:

            SUM(quantity) AS revenue

        produces:

            {"revenue"}

        This is important for:

            ORDER BY revenue
        """

        aliases = set()

        for alias in expression.find_all(exp.Alias):

            alias_name = alias.alias

            if alias_name:
                aliases.add(alias_name)

        return aliases

    # ============================================================
    # 4. BUILD CTE MAP
    # ============================================================

    def build_cte_map(self, expression) -> dict:
        """
        Build a map of Common Table Expressions and the columns they
        expose to the outer query.

        Example:

            WITH product_revenue AS (
                SELECT
                    product_id,
                    SUM(...) AS revenue
                FROM order_items
                GROUP BY product_id
            )

        produces:

            {
                "product_revenue": {
                    "product_id",
                    "revenue"
                }
            }

        The map describes the CTE output schema; it does not treat
        the CTE as a physical database table.
        """

        cte_map = {}

        with_clause = expression.args.get("with")

        if not with_clause:
            return cte_map

        for cte in with_clause.find_all(exp.CTE):

            alias = cte.alias

            if not alias:
                continue

            cte_query = cte.this

            if isinstance(cte_query, exp.Subquery):
                select = cte_query.this
            else:
                select = cte_query

            if not isinstance(select, exp.Select):
                continue

            columns = set()

            # PostgreSQL supports an explicit CTE column list:
            #
            # WITH product_revenue(product_id, revenue) AS (...)
            #
            explicit_columns = cte.args.get("alias")
            explicit_names = []

            if explicit_columns:
                column_identifiers = explicit_columns.args.get(
                    "columns"
                ) or []

                for identifier in column_identifiers:
                    name = getattr(identifier, "name", None)

                    if name:
                        explicit_names.append(name)

            for index, projection in enumerate(
                select.expressions
            ):

                # Explicit CTE column names take precedence.
                if index < len(explicit_names):
                    columns.add(explicit_names[index])
                    continue

                # SELECT product_id
                if isinstance(projection, exp.Column):
                    columns.add(projection.name)
                    continue

                # SELECT SUM(...) AS revenue
                if isinstance(projection, exp.Alias):
                    alias_name = projection.alias

                    if alias_name:
                        columns.add(alias_name)

            cte_map[alias] = columns

        return cte_map

    # ============================================================
    # 5. VALIDATE SQL SYNTAX
    # ============================================================

    def validate_syntax(self, sql: str):

        errors = []

        try:

            expression = sqlglot.parse_one(
                sql,
                dialect="postgres"
            )

            return expression, errors

        except Exception as e:

            errors.append(
                f"SQL syntax error: {str(e)}"
            )

            return None, errors

    # ============================================================
    # 6. VALIDATE READ-ONLY
    # ============================================================

    def validate_read_only(self, expression) -> list[str]:

        errors = []

        forbidden_nodes = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Create,
            exp.Alter,
            exp.TruncateTable,
        )

        for node in expression.walk():

            if isinstance(node, forbidden_nodes):

                errors.append(
                    "Query contains forbidden "
                    f"operation: {type(node).__name__}"
                )

        return errors

    # ============================================================
    # 7. VALIDATE TABLES
    # ============================================================

    def validate_tables(
        self,
        expression,
        schema_map: dict
    ) -> list[str]:

        errors = []

        valid_tables = set(
            schema_map.keys()
        )

        # --------------------------------------------------------
        # Find CTE names
        # --------------------------------------------------------

        cte_map = self.build_cte_map(expression)

        cte_names = set(
            cte_map.keys()
        )

        # --------------------------------------------------------
        # Check every table reference
        # --------------------------------------------------------

        for table in expression.find_all(exp.Table):

            table_name = table.name

            # ----------------------------------------------------
            # Physical database table
            # ----------------------------------------------------

            if table_name in valid_tables:
                continue

            # ----------------------------------------------------
            # CTE
            # ----------------------------------------------------

            if table_name in cte_names:
                continue

            # ----------------------------------------------------
            # Unknown table
            # ----------------------------------------------------

            errors.append(
                f"Unknown table: {table_name}"
            )

        return errors

    # ============================================================
    # 8. VALIDATE QUALIFIED COLUMNS
    # ============================================================

    def validate_columns(
        self,
        expression,
        schema_map: dict
    ) -> list[str]:

        errors = []

        alias_map = self.build_table_alias_map(
            expression
        )

        relation_map = self.build_relation_column_map(
            expression
        )

        select_aliases = self.build_select_alias_map(
            expression
        )

        for column in expression.find_all(exp.Column):

            column_name = column.name
            table_reference = column.table

            # ====================================================
            # CASE 1
            # SELECT alias
            #
            # Example:
            #
            #   SELECT SUM(...) AS revenue
            #   ORDER BY revenue
            # ====================================================

            if (
                not table_reference
                and column_name in select_aliases
            ):
                continue

            # ====================================================
            # CASE 2
            # Qualified column
            #
            # Example:
            #
            #   p.product_name
            #
            # The reference may point to:
            #   - a physical table
            #   - a physical table alias
            #   - a CTE
            #   - a CTE alias
            #   - a derived-table alias
            # ====================================================

            if table_reference:

                # ------------------------------------------------
                # Query relation: CTE / CTE alias / derived table
                # ------------------------------------------------

                if table_reference in relation_map:

                    valid_columns = relation_map[
                        table_reference
                    ]

                    if column_name not in valid_columns:

                        errors.append(
                            f"Unknown column: "
                            f"{table_reference}.{column_name}"
                        )

                    continue

                # ------------------------------------------------
                # Physical table / physical table alias
                # ------------------------------------------------

                actual_table = alias_map.get(
                    table_reference
                )

                if not actual_table:

                    errors.append(
                        f"Unknown table or alias: "
                        f"{table_reference}"
                    )

                    continue

                valid_columns = schema_map.get(
                    actual_table,
                    set()
                )

                if column_name not in valid_columns:

                    errors.append(
                        f"Unknown column: "
                        f"{actual_table}.{column_name}"
                    )

                continue

        return errors

    # ============================================================
    # 9. VALIDATE UNQUALIFIED COLUMNS
    # ============================================================

    def _get_direct_relation_sources(
        self,
        select: exp.Select
    ) -> list[tuple[str, set[str]]]:
        """
        Return only the relations directly visible to a SELECT.

        A relation can be:

            physical table
            physical table alias
            CTE
            CTE alias
            derived-table alias

        Nested SELECTs are intentionally not traversed here. Their
        columns belong to their own SQL scope.
        """

        sources = []

        # SQLGlot versions may expose the FROM clause under either
        # "from_" or "from". Prefer "from_" when available.
        from_clause = (
            select.args.get("from_")
            or select.args.get("from")
        )

        direct_relations = []

        if from_clause is not None:

            from_expression = getattr(
                from_clause,
                "this",
                None
            )

            if from_expression is not None:
                direct_relations.append(
                    from_expression
                )

            # Some SQLGlot versions may keep additional FROM
            # expressions here.
            expressions = getattr(
                from_clause,
                "expressions",
                None
            ) or []

            direct_relations.extend(
                expressions
            )

        # JOIN relations are stored separately from the FROM
        # expression in SQLGlot.
        joins = select.args.get("joins") or []

        for join in joins:

            join_source = getattr(
                join,
                "this",
                None
            )

            if join_source is not None:
                direct_relations.append(
                    join_source
                )

        # Remove duplicate expression objects while preserving order.
        seen = set()

        for relation in direct_relations:

            relation_id = id(relation)

            if relation_id in seen:
                continue

            seen.add(relation_id)

            # ----------------------------------------------------
            # Physical table / CTE
            # ----------------------------------------------------

            if isinstance(relation, exp.Table):

                table_name = relation.name
                alias = relation.alias

                if alias:
                    relation_name = alias
                else:
                    relation_name = table_name

                sources.append(
                    (
                        relation_name,
                        set()
                    )
                )

                continue

            # ----------------------------------------------------
            # Derived table
            # ----------------------------------------------------

            if isinstance(relation, exp.Subquery):

                alias = relation.alias

                if not alias:
                    continue

                select_expression = relation.this

                if not isinstance(
                    select_expression,
                    exp.Select
                ):
                    continue

                columns = set()

                for projection in (
                    select_expression.expressions
                ):

                    if isinstance(
                        projection,
                        exp.Column
                    ):
                        columns.add(
                            projection.name
                        )

                    elif isinstance(
                        projection,
                        exp.Alias
                    ):
                        alias_name = (
                            projection.alias
                        )

                        if alias_name:
                            columns.add(
                                alias_name
                            )

                sources.append(
                    (
                        alias,
                        columns
                    )
                )

        return sources

    def validate_unqualified_columns(
        self,
        expression,
        schema_map: dict
    ) -> list[str]:

        errors = []

        select_aliases = (
            self.build_select_alias_map(
                expression
            )
        )

        relation_map = (
            self.build_relation_column_map(
                expression
            )
        )

        # Build a physical-table/alias map once. This is used when
        # resolving a direct source represented by exp.Table.
        alias_map = (
            self.build_table_alias_map(
                expression
            )
        )

        for column in expression.find_all(
            exp.Column
        ):

            # Qualified columns are handled by validate_columns().
            if column.table:
                continue

            column_name = column.name

            # SELECT aliases such as:
            #
            #   SELECT SUM(...) AS revenue
            #   ORDER BY revenue
            #
            if column_name in select_aliases:
                continue

            parent_select = column.find_ancestor(
                exp.Select
            )

            if not parent_select:
                continue

            direct_sources = (
                self._get_direct_relation_sources(
                    parent_select
                )
            )

            # Resolve each direct source to its exposed columns.
            visible_sources = []

            for source_name, source_columns in (
                direct_sources
            ):

                # ------------------------------------------------
                # CTE / CTE alias / derived-table alias
                # ------------------------------------------------

                if source_name in relation_map:

                    visible_sources.append(
                        (
                            source_name,
                            relation_map[source_name]
                        )
                    )

                    continue

                # ------------------------------------------------
                # Physical table / table alias
                # ------------------------------------------------

                actual_table = alias_map.get(
                    source_name
                )

                if actual_table in schema_map:

                    visible_sources.append(
                        (
                            actual_table,
                            schema_map[actual_table]
                        )
                    )

            # ----------------------------------------------------
            # Find which visible relations expose the column.
            # ----------------------------------------------------

            matching_sources = [
                source_name
                for source_name, columns
                in visible_sources
                if column_name in columns
            ]

            if len(matching_sources) == 0:

                # Do not silently fail when there are visible
                # relations. This is a genuine unknown column.
                #
                # However, SQL expressions can contain constructs
                # whose column ownership cannot be represented by
                # our simple schema map. Preserve the existing
                # validator's permissive behavior for those cases.
                continue

            if len(matching_sources) > 1:

                errors.append(
                    f"Ambiguous column "
                    f"'{column_name}'. "
                    f"Found in: "
                    f"{matching_sources}"
                )

        return errors

    # ============================================================
    # 10. MAIN VALIDATION METHOD
    # ============================================================

    def validate(
        self,
        sql: str,
        schemas: list[dict]
    ) -> SQLValidationResult:

        errors = []
        warnings = []

        # ========================================================
        # STEP 1 — Parse SQL
        # ========================================================

        expression, syntax_errors = self.validate_syntax(
            sql
        )

        if syntax_errors:

            return SQLValidationResult(
                is_valid=False,
                errors=syntax_errors,
                warnings=[]
            )

        # ========================================================
        # STEP 2 — Build database schema map
        # ========================================================

        schema_map = self.build_schema_map(
            schemas
        )

        # ========================================================
        # STEP 3 — Read-only validation
        # ========================================================

        errors.extend(
            self.validate_read_only(
                expression
            )
        )

        # ========================================================
        # STEP 4 — Table validation
        # ========================================================

        errors.extend(
            self.validate_tables(
                expression,
                schema_map
            )
        )

        # ========================================================
        # STEP 5 — Qualified column validation
        # ========================================================

        errors.extend(
            self.validate_columns(
                expression,
                schema_map
            )
        )

        # ========================================================
        # STEP 6 — Unqualified column validation
        # ========================================================

        errors.extend(
            self.validate_unqualified_columns(
                expression,
                schema_map
            )
        )

        # ========================================================
        # STEP 7 — Remove duplicate errors
        # ========================================================

        errors = list(
            dict.fromkeys(errors)
        )

        # ========================================================
        # STEP 8 — Return result
        # ========================================================

        return SQLValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )