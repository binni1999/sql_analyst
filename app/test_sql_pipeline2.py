from database.service import DatabaseService
from database.schema_formatter import (
    format_database_schema_for_llm
)

from agents.sql_generator import SQLGenerator
from agents.sql_validator import SQLValidator


def validate_sql(
    sql,
    validator,
    db,
    schemas
):

    print("\nSQL")
    print("=" * 60)

    print(sql)

    # -----------------------------------------
    # SQLGlot validation
    # -----------------------------------------

    validation = validator.validate(
        sql=sql,
        schemas=schemas
    )

    print("\nSQLGLOT VALIDATION")
    print("=" * 60)

    print(
        f"Valid: {validation.is_valid}"
    )

    print(
        f"Errors: {validation.errors}"
    )

    # -----------------------------------------
    # PostgreSQL validation
    # -----------------------------------------

    if validation.is_valid:

        database_validation = (
            db.validate_with_database(sql)
        )

        print("\nPOSTGRESQL VALIDATION")
        print("=" * 60)

        print(
            f"Valid: "
            f"{database_validation['valid']}"
        )

        print(
            f"Error: "
            f"{database_validation['error']}"
        )

        return database_validation

    return None


def main():

    # -----------------------------------------
    # Database
    # -----------------------------------------

    db = DatabaseService()

    # -----------------------------------------
    # Schema
    # -----------------------------------------

    schemas = db.get_full_schema()

    schema_text = (
        format_database_schema_for_llm(
            schemas
        )
    )

    # -----------------------------------------
    # Agents
    # -----------------------------------------

    generator = SQLGenerator()

    validator = SQLValidator()

    # =========================================
    # TEST 1
    # LLM generated SQL
    # =========================================

    print("\n")
    print("#" * 70)
    print("TEST 1 — LLM GENERATED SQL")
    print("#" * 70)

    question = """
    What are the top 5 products by revenue?
    """

    generated = generator.generate(
        question=question,
        schema=schema_text
    )

    print("\nGENERATED SQL")
    print("=" * 60)

    print(generated.sql)

    validate_sql(
        generated.sql,
        validator,
        db,
        schemas
    )

    # =========================================
    # TEST 2
    # Invalid column
    # =========================================

    print("\n")
    print("#" * 70)
    print("TEST 2 — INVALID COLUMN")
    print("#" * 70)

    invalid_column_sql = """
    SELECT
        p.fake_column
    FROM products AS p;
    """

    validate_sql(
        invalid_column_sql,
        validator,
        db,
        schemas
    )

    # =========================================
    # TEST 3
    # PostgreSQL semantic error
    # =========================================

    print("\n")
    print("#" * 70)
    print("TEST 3 — POSTGRESQL SEMANTIC ERROR")
    print("#" * 70)

    invalid_group_by_sql = """
    SELECT
        p.product_name,
        p.product_id,
        SUM(oi.quantity) AS total_quantity
    FROM products AS p
    JOIN order_items AS oi
        ON oi.product_id = p.product_id
    GROUP BY p.product_name
    ORDER BY total_quantity DESC
    LIMIT 5;
    """

    validate_sql(
        invalid_group_by_sql,
        validator,
        db,
        schemas
    )


if __name__ == "__main__":
    main()