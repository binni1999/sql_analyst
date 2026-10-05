from database.service import DatabaseService
from agents.sql_executor import SQLExecutor


def main():

    # -----------------------------------------
    # Database
    # -----------------------------------------

    db = DatabaseService()

    # -----------------------------------------
    # Executor
    # -----------------------------------------

    executor = SQLExecutor(db)

    # -----------------------------------------
    # Test SQL
    # -----------------------------------------

    sql = """
SELECT
    p.product_name,
    SUM(oi.non_existing_column)
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY p.product_name;
"""

    # -----------------------------------------
    # Execute
    # -----------------------------------------

    result = executor.execute(sql)

    # -----------------------------------------
    # Print result
    # -----------------------------------------

    print("\nEXECUTOR RESULT")
    print("=" * 60)

    print(
        "Success:",
        result["success"]
    )

    print(
        "\nColumns:",
        result["columns"]
    )

    print("\nRows:")

    for row in result["rows"]:
        print(row)

    print(
        "\nError:",
        result["error"]
    )


if __name__ == "__main__":
    main()