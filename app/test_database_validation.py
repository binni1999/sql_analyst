# pyrefly: ignore [missing-import]
from database.service import DatabaseService


def main():

    db = DatabaseService()

    sql = """
    SELECT
        p.product_id,
        p.fake_column,
        SUM(
            oi.quantity * oi.unit_price
            - COALESCE(oi.discount, 0)
        ) AS revenue
    FROM order_items AS oi
    JOIN products AS p
        ON oi.product_id = p.product_id
    GROUP BY
        p.product_id,
        p.product_name
    ORDER BY revenue DESC
    LIMIT 5;
    """

    result = db.validate_with_database(sql)

    print("=" * 60)
    print("DATABASE VALIDATION RESULT")
    print("=" * 60)

    print(f"Valid: {result['valid']}")
    print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()