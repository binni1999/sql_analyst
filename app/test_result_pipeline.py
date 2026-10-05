from agents.sql_agent import SQLAgent
from agents.sql_generator import SQLGenerator
from agents.sql_validator import SQLValidator
from agents.sql_executor import SQLExecutor
from agents.result_analyzer import ResultAnalyzer
from database.service import DatabaseService


def main():

    # =========================================
    # 1. User question
    # =========================================

    question = "Show the top 5 products by revenue"

    # =========================================
    # 2. Create services
    # =========================================

    db = DatabaseService()

    sql_generator = SQLGenerator()

    sql_validator = SQLValidator()

    sql_agent = SQLAgent(
        sql_generator=sql_generator,
        sql_validator=sql_validator,
        db=db,
        max_retries=3
    )

    sql_executor = SQLExecutor(db)

    result_analyzer = ResultAnalyzer()

    # =========================================
    # 3. Get complete database schema
    # =========================================

    schemas = db.get_full_schema()

    # =========================================
    # 4. Build schema text
    # =========================================

    schema_text = ""

    for schema in schemas:

        schema_text += (
            f"\nTABLE {schema['table']}\n"
        )

        schema_text += "\nColumns:\n"

        for column in schema["columns"]:

            schema_text += (
                f"- {column['name']} "
                f"{column['type']}\n"
            )

        if schema["primary_keys"]:

            schema_text += "\nPrimary Keys:\n"

            for pk in schema["primary_keys"]:

                schema_text += (
                    f"- {pk}\n"
                )

        if schema["foreign_keys"]:

            schema_text += "\nForeign Keys:\n"

            for fk in schema["foreign_keys"]:

                schema_text += (
                    f"- {fk['column']} "
                    f"→ "
                    f"{fk['references_table']}."
                    f"{fk['references_column']}\n"
                )

    # =========================================
    # 5. Generate + validate SQL
    # =========================================

    print("\nSTEP 1 — SQL AGENT")
    print("=" * 60)

    sql_result = sql_agent.generate_valid_sql(
        question=question,
        schema=schema_text,
        schemas=schemas
    )

    if not sql_result["success"]:

        print(
            "\nSQL Agent failed."
        )

        print(
            "Errors:",
            sql_result["errors"]
        )

        return

    sql = sql_result["sql"]

    print("\nVALID SQL")
    print("=" * 60)
    print(sql)

    # =========================================
    # 6. Execute SQL
    # =========================================

    print("\nSTEP 2 — SQL EXECUTOR")
    print("=" * 60)

    execution_result = sql_executor.execute(sql)

    if not execution_result["success"]:

        print(
            "\nSQL execution failed."
        )

        print(
            "Error:",
            execution_result["error"]
        )

        return

    print("\nRAW DATABASE RESULT")
    print("=" * 60)

    print(
        "Columns:",
        execution_result["columns"]
    )

    print("Rows:")

    for row in execution_result["rows"]:
        print(row)

    # =========================================
    # 7. Analyze result
    # =========================================

    print("\nSTEP 3 — RESULT ANALYZER")
    print("=" * 60)

    analyzed_result = result_analyzer.analyze(
        execution_result
    )

    print("\nANALYZED RESULT")
    print("=" * 60)

    print(
        "Row count:",
        analyzed_result["row_count"]
    )

    print(
        "Columns:",
        analyzed_result["columns"]
    )

    print(
        "Is empty:",
        analyzed_result["is_empty"]
    )

    print("\nData:")

    for record in analyzed_result["data"]:
        print(record)


if __name__ == "__main__":
    main()