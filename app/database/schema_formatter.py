def format_schema_for_llm(schema: dict) -> str:

    lines = []

    table_name = schema["table"]

    lines.append(f"TABLE: {table_name}")

    lines.append("")
    lines.append("Columns:")

    for column in schema["columns"]:

        lines.append(
            f"- {column['name']} "
            f"{column['type'].upper()}"
        )

    if schema["primary_keys"]:

        lines.append("")
        lines.append("Primary Keys:")

        for primary_key in schema["primary_keys"]:

            lines.append(
                f"- {primary_key}"
            )

    if schema["foreign_keys"]:

        lines.append("")
        lines.append("Relationships:")

        for foreign_key in schema["foreign_keys"]:

            lines.append(
                f"- {foreign_key['column']} "
                f"-> "
                f"{foreign_key['references_table']}."
                f"{foreign_key['references_column']}"
            )


    return "\n".join(lines)


def format_database_schema_for_llm(
    schemas: list[dict]
) -> str:

    formatted_tables = []

    for schema in schemas:

        formatted_tables.append(
            format_schema_for_llm(schema)
        )

    return "\n\n".join(
        formatted_tables
    )