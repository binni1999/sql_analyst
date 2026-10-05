# pyrefly: ignore [missing-import]
from sqlalchemy import text
# pyrefly: ignore [missing-import]

from sqlalchemy.exc import SQLAlchemyError
import sqlglot
from sqlglot import exp
try:
    from .dbconnect import engine
except ImportError as e:
    if "relative import" in str(e):
        # pyrefly: ignore [missing-import]
        from dbconnect import engine
    else:
        raise





class DatabaseService:

    def get_tables(self):
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)

        with engine.connect() as connection:

            result = connection.execute(query)

            return [
                row[0]
                for row in result
            ]


    def get_schema(self, table_name: str):

        # --------------------------------------------------
        # 1. Get columns
        # --------------------------------------------------

        columns_query = text("""
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            ORDER BY ordinal_position;
        """)


        # --------------------------------------------------
        # 2. Get primary keys
        # --------------------------------------------------

        primary_keys_query = text("""
            SELECT
                kcu.column_name
            FROM information_schema.table_constraints tc

            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
                AND tc.table_name = kcu.table_name

            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = :table_name

            ORDER BY kcu.ordinal_position;
        """)


        # --------------------------------------------------
        # 3. Get foreign keys
        # --------------------------------------------------

        foreign_keys_query = text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS references_table,
                ccu.column_name AS references_column

            FROM information_schema.table_constraints tc

            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
                AND tc.table_name = kcu.table_name

            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema

            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = :table_name

            ORDER BY kcu.ordinal_position;
        """)


        # --------------------------------------------------
        # Execute all metadata queries
        # --------------------------------------------------

        with engine.connect() as connection:

            # Columns
            column_result = connection.execute(
                columns_query,
                {
                    "table_name": table_name
                }
            )

            columns = [
                {
                    "name": row.column_name,
                    "type": row.data_type
                }
                for row in column_result
            ]


            # Primary keys
            primary_key_result = connection.execute(
                primary_keys_query,
                {
                    "table_name": table_name
                }
            )

            primary_keys = [
                row.column_name
                for row in primary_key_result
            ]


            # Foreign keys
            foreign_key_result = connection.execute(
                foreign_keys_query,
                {
                    "table_name": table_name
                }
            )

            foreign_keys = [
                {
                    "column": row.column_name,
                    "references_table": row.references_table,
                    "references_column": row.references_column
                }
                for row in foreign_key_result
            ]


        # --------------------------------------------------
        # Return structured schema
        # --------------------------------------------------

        return {
            "table": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }

    def get_full_schema(self):
        tables = self.get_tables()
        return [
            self.get_schema(table)
            for table in tables
        ]



    def execute_query(self, sql: str):

        # -----------------------------------------
        # Parse SQL
        # -----------------------------------------

        try:

            expression = sqlglot.parse_one(
                sql,
                dialect="postgres"
            )

        except Exception as e:
            raise ValueError(
                f"Invalid SQL: {str(e)}"
            )

        # -----------------------------------------
        # Only allow SELECT
        # -----------------------------------------

        if not isinstance(expression, exp.Select):

            raise ValueError(
                "Only SELECT queries are allowed."
            )

        # -----------------------------------------
        # Execute
        # -----------------------------------------

        with engine.connect() as connection:

            result = connection.execute(
                text(sql)
            )

            columns = list(result.keys())
            rows = result.fetchall()

            return {
                "columns": columns,
                "rows": [
                    list(row)
                    for row in rows
                ]
            }

    def execute_query_secure(
        self,
        sql: str,
        *,
        timeout_ms: int,
        max_result_rows: int,
    ):
        """Execute an already-guarded SELECT with DB-level safety controls."""
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero")
        if max_result_rows <= 0:
            raise ValueError("max_result_rows must be greater than zero")

        with engine.connect() as connection:
            # set_config(..., true) makes statement_timeout local to the
            # current transaction and avoids changing the pooled session.
            connection.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": f"{timeout_ms}ms"},
            )

            result = connection.execute(text(sql))
            columns = list(result.keys())
            rows = result.fetchmany(max_result_rows + 1)

            if len(rows) > max_result_rows:
                raise ValueError(
                    "Query returned more rows than the configured maximum "
                    f"of {max_result_rows}."
                )

            return {
                "columns": columns,
                "rows": [list(row) for row in rows],
            }


    def validate_query(self, sql: str):

        validation_sql = f"""
        EXPLAIN
        {sql}
        """

        with engine.connect() as connection:

            try:

                connection.execute(
                    text(validation_sql)
                )

                return {
                    "is_valid": True,
                    "error": None
                }

            except Exception as e:

                return {
                    "is_valid": False,
                    "error": str(e)
                }

    def validate_with_database(self, sql: str):
        explain_sql = f"EXPLAIN {sql}"

        try:

            with engine.connect() as connection:

                connection.execute(
                    text(explain_sql)
                )

                return {
                    "valid": True,
                    "error": None
                }

        except Exception as e:

            return {
                "valid": False,
                "error": str(e)
            }