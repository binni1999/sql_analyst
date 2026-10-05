from database.service import DatabaseService
from agents.sql_validator import SQLValidator


def main():

    db = DatabaseService()

    schemas = db.get_full_schema()

    validator = SQLValidator()


    # -----------------------------------------
    # TEST 1
    # -----------------------------------------

    sql = """
    SELECT
        customer_id,
        name
    FROM customers;
    """

    result = validator.validate(
        sql,
        schemas
    )

    print("\nTEST 1")
    print("=" * 50)
    print(result)


    # -----------------------------------------
    # TEST 2
    # -----------------------------------------

    sql = """
    SELECT
        p.product_name,
        p.price
    FROM products p;
    """

    result = validator.validate(
        sql,
        schemas
    )

    print("\nTEST 2")
    print("=" * 50)
    print(result)


    # -----------------------------------------
    # TEST 3
    # -----------------------------------------

    sql = """
    SELECT
        p.product_name,
        p.does_not_exist
    FROM products p;
    """

    result = validator.validate(
        sql,
        schemas
    )

    print("\nTEST 3")
    print("=" * 50)
    print(result)


    # -----------------------------------------
    # TEST 4
    # -----------------------------------------

    sql = """
    SELECT *
    FROM product;
    """

    result = validator.validate(
        sql,
        schemas
    )

    print("\nTEST 4")
    print("=" * 50)
    print(result)


    # -----------------------------------------
    # TEST 5
    # -----------------------------------------

    sql = """
    DELETE FROM customers;
    """

    result = validator.validate(
        sql,
        schemas
    )

    print("\nTEST 5")
    print("=" * 50)
    print(result)


if __name__ == "__main__":
    main()