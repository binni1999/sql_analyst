import test_answer_generator
from database.service import DatabaseService
from database.schema_formatter import (
    format_database_schema_for_llm
)

from agents.result_analyzer import ResultAnalyzer
from agents.answer_generator import AnswerGenerator
# pyrefly: ignore [missing-import]
from agents.sql_generator import SQLGenerator
# pyrefly: ignore [missing-import]
from agents.sql_validator import SQLValidator


def main():

    # -----------------------------------------
    # Database
    # -----------------------------------------

    db = DatabaseService()
    


    # -----------------------------------------
    # Get schema
    # -----------------------------------------

    schemas = db.get_full_schema()

    schema_text = (
        format_database_schema_for_llm(
            schemas
        )
    )


    # -----------------------------------------
    # Create agents
    # -----------------------------------------

    generator = SQLGenerator()

    validator = SQLValidator()
    analyzer = ResultAnalyzer()
    answer_generator = AnswerGenerator()


    # -----------------------------------------
    # User question
    # -----------------------------------------

    question = """
    What are the top 5 products by revenue?
    """


    # -----------------------------------------
    # Generate SQL
    # -----------------------------------------

    generated = generator.generate(
        question=question,
        schema=schema_text
    )


    print("\nGENERATED SQL")
    print("=" * 60)

    print(generated.sql)


    # -----------------------------------------
    # Validate SQL
    # -----------------------------------------

    validation = validator.validate(
        sql=generated.sql,
        schemas=schemas
    )


    print("\nVALIDATION RESULT")
    print("=" * 60)

    print(
        f"Valid: {validation.is_valid}"
    )

    print(
        f"Errors: {validation.errors}"
    )
# ============================================
# PostgreSQL validation
# ============================================

    if validation.is_valid:

        database_validation = db.validate_with_database(
            #generated.sql
             """
SELECT p.product_id,
       p.product_name,
       SUM((oi.unit_price - oi.discount) * oi.quantity) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC
LIMIT 5;
"""
        )

        print()
        print("POSTGRESQL VALIDATION")
        print("=" * 60)

        print(
            f"Valid: "
            f"{database_validation['valid']}"
        )

        print(
            f"Error: "
            f"{database_validation['error']}"
        )


        if database_validation["valid"]:

            result = db.execute_query(
                generated.sql
            )

            print("\nEXECUTION RESULT")
            print("=" * 60)

            print(
            f"Columns: {result['columns']}"
            )

            print("Rows:")

            for row in result["rows"]:
                print(row)

            # -----------------------------------------
            # Result Analyzer
            # -----------------------------------------

            analyzed_result = analyzer.analyze(
                result
            )
            answer = answer_generator.generate(
                question,
                analyzed_result
            )

            print("\nFINAL ANSWER")
            print("=" * 60)
            print(answer)

            print(
                f"Row count: "
                f"{analyzed_result['row_count']}"
            )

            print(
                f"Is empty: "
                f"{analyzed_result['is_empty']}"
            )

            print("\nData:")

            for row in analyzed_result["data"]:
                print(row)

        


if __name__ == "__main__":
    main()