try:
    from database.service import DatabaseService
except ModuleNotFoundError:
    from app.database.service import DatabaseService



db = DatabaseService()
tables = db.get_tables()

print("\nAvailable tables:")
print(tables)


for table in tables:

    print("\n" + "=" * 60)
    print(f"SCHEMA FOR: {table}")
    print("=" * 60)

    schema = db.get_schema(table)

    print(schema)

# print("=" * 50)
# print("DATABASE TABLES")
# print("=" * 50)

# tables = db.get_tables()

# print(tables)


# print("\n")


# for table in tables:

#     print("=" * 50)
#     print(f"SCHEMA: {table}")
#     print("=" * 50)

#     schema = db.get_schema(table)

#     for column in schema:

#         print(
#             f"{column['column_name']}"
#             f" -> "
#             f"{column['data_type']}"
#         )

# print("\n")
# print("=" * 50)
# print("TEST QUERY")
# print("=" * 50)


# result = db.execute_query(
#     """
#     SELECT COUNT(*) AS total_customers
#     FROM customers;
#     """
# )


# print(result)

# result = db.execute_query(
#     """
#     SELECT
#         p.product_name,
#         SUM(
#             oi.quantity * oi.unit_price
#         ) AS revenue
#     FROM products p
#     JOIN order_items oi
#         ON p.product_id = oi.product_id
#     GROUP BY p.product_name
#     ORDER BY revenue DESC
#     LIMIT 5;
#     """
# )

# print(result)