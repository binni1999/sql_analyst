from agents.sql_agent import SQLAgent
from agents.sql_generator import SQLGenerator
from agents.sql_validator import SQLValidator
from database.service import DatabaseService


def main():

    question = "Show the top 5 products by revenue"

    # -----------------------------------------
    # Create services
    # -----------------------------------------

    db = DatabaseService()

    sql_generator = SQLGenerator()

    sql_validator = SQLValidator()

    # -----------------------------------------
    # Create SQL Agent
    # -----------------------------------------

    agent = SQLAgent(
        sql_generator=sql_generator,
        sql_validator=sql_validator,
        db=db,
        max_retries=3
    )

    # -----------------------------------------
    # Get complete database schema
    # -----------------------------------------

    schemas = db.get_full_schema()

    print("\nDATABASE SCHEMA")
    print("=" * 60)

    for schema in schemas:

        print(f"\nTABLE: {schema['table']}")

        print("Columns:")

        for column in schema["columns"]:
            print(
                f"  - {column['name']} "
                f"{column['type']}"
            )

        print(
            f"Primary Keys: "
            f"{schema['primary_keys']}"
        )

        print(
            f"Foreign Keys: "
            f"{schema['foreign_keys']}"
        )

    # -----------------------------------------
    # Build schema text for LLM
    # -----------------------------------------

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

    print("\nLLM SCHEMA")
    print("=" * 60)
    print(schema_text)

    # -----------------------------------------
    # Generate valid SQL
    # -----------------------------------------

    result = agent.generate_valid_sql(
        question=question,
        schema=schema_text,
        schemas=schemas
    )

    # -----------------------------------------
    # Final result
    # -----------------------------------------

    print("\nFINAL SQL AGENT RESULT")
    print("=" * 60)

    print(
        f"Success: {result['success']}"
    )

    print(
        f"Attempts: {result['attempts']}"
    )

    print("\nSQL:")
    print(result["sql"])

    print("\nErrors:")

    if result["errors"]:
        for error in result["errors"]:
            print(f"- {error}")
    else:
        print("None")


if __name__ == "__main__":
    main()