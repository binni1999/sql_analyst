from typing import Any


def build_deterministic_answer(
    analysis: dict[str, Any] | None,
    max_rows: int = 10,
) -> str | None:
    """Format analytics results without making another LLM call."""
    if not isinstance(analysis, dict):
        return None

    if not isinstance(max_rows, int) or max_rows < 1:
        return None

    columns = analysis.get("columns")
    rows = analysis.get("rows")

    if not isinstance(columns, list) or not columns:
        return None

    if not all(isinstance(column, str) for column in columns):
        return None

    if not isinstance(rows, list):
        return None

    if not rows:
        return "The query completed successfully but returned no rows."

    lines = ["The query returned the following results:"]

    for row in rows[:max_rows]:
        if not isinstance(row, (list, tuple)):
            return None

        values = []
        for index, column in enumerate(columns):
            value = row[index] if index < len(row) else None
            values.append(f"{column}: {value}")

        lines.append("- " + "; ".join(values))

    remaining = len(rows) - max_rows
    if remaining > 0:
        lines.append(
            f"...and {remaining} additional row(s) not shown."
        )

    return "\n".join(lines)
