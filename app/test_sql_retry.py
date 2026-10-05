from agents.sql_validator import SQLValidator
from agents.sql_agent import SQLAgent


class FakeSQLGenerator:

    def __init__(self):

        self.call_count = 0

    def generate(
        self,
        question,
        schema
    ):

        class Result:
            sql = """
            SELECT
                p.product_name,
                SUM(oi.price * oi.quantity) AS revenue
            FROM products p
            JOIN order_items oi
                ON p.product_id = oi.product_id
            GROUP BY p.product_name
            ORDER BY revenue DESC
            LIMIT 5;
            """

        return Result()

    def fix_sql(
        self,
        question,
        sql,
        errors,
        schema
    ):

        self.call_count += 1

        print(
            f"\nFakeSQLGenerator.fix_sql() "
            f"called: {self.call_count}"
        )

        return """
        SELECT
            p.product_name,
            SUM(oi.unit_price * oi.quantity) AS revenue
        FROM products p
        JOIN order_items oi
            ON p.product_id = oi.product_id
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT 5;
        """


def main():

    generator = FakeSQLGenerator()

    validator = SQLValidator()

    agent = SQLAgent(
        sql_generator=generator,
        sql_validator=validator,
        max_retries=3
    )

    question = (
        "What are the top 5 products by revenue?"
    )

    schema = """
TABLE products

Columns:
- product_id INTEGER
- product_name VARCHAR

TABLE order_items

Columns:
- product_id INTEGER
- quantity INTEGER
- unit_price NUMERIC
"""

    schemas = [
        {
            "table": "products",
            "columns": [
                {
                    "name": "product_id",
                    "type": "integer"
                },
                {
                    "name": "product_name",
                    "type": "varchar"
                }
            ]
        },
        {
            "table": "order_items",
            "columns": [
                {
                    "name": "product_id",
                    "type": "integer"
                },
                {
                    "name": "quantity",
                    "type": "integer"
                },
                {
                    "name": "unit_price",
                    "type": "numeric"
                }
            ]
        }
    ]

    result = agent.generate_valid_sql(
        question=question,
        schema=schema,
        schemas=schemas
    )

    print("\nFINAL RESULT")
    print("=" * 60)

    print("Success:", result["success"])
    print("Attempts:", result["attempts"])

    print("\nFinal SQL:")
    print(result["sql"])

    print("\nErrors:")
    print(result["errors"])


if __name__ == "__main__":
    main()