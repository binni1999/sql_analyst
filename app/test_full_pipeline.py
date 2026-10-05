from agents.sql_agent import SQLAgent
from agents.sql_generator import SQLGenerator
from agents.sql_validator import SQLValidator
from agents.sql_executor import SQLExecutor
from agents.result_analyzer import ResultAnalyzer
from agents.answer_generator import AnswerGenerator
from database.service import DatabaseService


def main():

    # =========================================
    # 1. User Question
    # =========================================

    question = "Show customers from a city called Atlantis"

    print("\nUSER QUESTION")
    print("=" * 60)
    print(question)

    # =========================================
    # 2. Create Database Service
    # =========================================

    db = DatabaseService()

    # =========================================
    # 3. Create SQL components
    # =========================================

    sql_generator = SQLGenerator()

    sql_validator = SQLValidator()

    sql_agent = SQLAgent(
        sql_generator=sql_generator,
        sql_validator=sql_validator,
        db=db,
        max_retries=3
    )

    # =========================================
    # 4. Create Executor
    # =========================================

    sql_executor = SQLExecutor(db)

    # =========================================
    # 5. Create Result Analyzer
    # =========================================

    result_analyzer = ResultAnalyzer()

    # =========================================
    # 6. Create Answer Generator
    # =========================================

    answer_generator = AnswerGenerator()

    # =========================================
    # 7. Get Complete Database Schema
    # =========================================

    schemas = db.get_full_schema()

    # =========================================
    # 8. Build Schema Text
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
    # 9. SQL Agent
    # =========================================

    print("\n\nSTEP 1 — SQL AGENT")
    print("=" * 60)

    sql_result = sql_agent.generate_valid_sql(
        question=question,
        schema=schema_text,
        schemas=schemas
    )

    if not sql_result["success"]:

        print("\nSQL Agent failed.")

        for error in sql_result["errors"]:
            print(f"- {error}")

        return

    sql = sql_result["sql"]

    print("\nFINAL VALID SQL")
    print("=" * 60)
    print(sql)

    # =========================================
    # 10. SQL Executor
    # =========================================

    print("\n\nSTEP 2 — SQL EXECUTOR")
    print("=" * 60)

    execution_result = sql_executor.execute(sql)

    if not execution_result["success"]:

        print("\nSQL execution failed.")

        print(
            execution_result["error"]
        )

        return

    print("\nRaw database result received.")

    # =========================================
    # 11. Result Analyzer
    # =========================================

    print("\n\nSTEP 3 — RESULT ANALYZER")
    print("=" * 60)

    analyzed_result = result_analyzer.analyze(
        execution_result
    )

    print(
        "Row count:",
        analyzed_result["row_count"]
    )

    print(
        "Is empty:",
        analyzed_result["is_empty"]
    )

    print("\nAnalyzed data:")

    for record in analyzed_result["data"]:
        print(record)

    # =========================================
    # 12. Answer Generator
    # =========================================

    print("\n\nSTEP 4 — ANSWER GENERATOR")
    print("=" * 60)

    answer = answer_generator.generate(
        question,
        analyzed_result
    )

    # =========================================
    # 13. Final Answer
    # =========================================

    print("\nFINAL ANSWER")
    print("=" * 60)

    print(answer)


if __name__ == "__main__":
    main()