from database.service import DatabaseService
from database.schema_formatter import (
    format_database_schema_for_llm
)
from agents.sql_generator import SQLGenerator


def main():

    # ----------------------------------------
    # 1. Connect to database
    # ----------------------------------------

    db = DatabaseService()


    # ----------------------------------------
    # 2. Get complete database schema
    # ----------------------------------------

    schemas = db.get_full_schema()


    # ----------------------------------------
    # 3. Convert schema into LLM format
    # ----------------------------------------

    schema_text = format_database_schema_for_llm(
        schemas
    )


    # ----------------------------------------
    # 4. Create SQL Generator
    # ----------------------------------------

    generator = SQLGenerator()


    # ----------------------------------------
    # 5. User question
    # ----------------------------------------

    question = """
    What is the average employee salary?
    """


    # ----------------------------------------
    # 6. Generate SQL
    # ----------------------------------------

    result = generator.generate(
        question=question,
        schema=schema_text
    )


    # ----------------------------------------
    # 7. Display result
    # ----------------------------------------

    print("\n" + "=" * 60)
    print("GENERATED SQL")
    print("=" * 60)

    print(result.sql)


    print("\n" + "=" * 60)
    print("TABLES USED")
    print("=" * 60)

    print(result.tables_used)


    print("\n" + "=" * 60)
    print("EXPLANATION")
    print("=" * 60)

    print(result.explanation)


if __name__ == "__main__":
    main()