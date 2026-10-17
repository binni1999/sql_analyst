from sqlalchemy import text

from database.dbconnect import readonly_engine


def test_readonly_database_role_has_select_but_no_write_permissions():
    with readonly_engine.connect() as connection:
        role = connection.execute(
            text("SELECT current_user")
        ).scalar_one()

        assert role == "datapilot_readonly"

        permissions = connection.execute(
            text("""
                SELECT
                    has_table_privilege(current_user, 'customers', 'SELECT'),
                    has_table_privilege(current_user, 'customers', 'INSERT'),
                    has_table_privilege(current_user, 'customers', 'UPDATE'),
                    has_table_privilege(current_user, 'customers', 'DELETE')
            """)
        ).one()

    can_select, can_insert, can_update, can_delete = permissions

    assert can_select is True
    assert can_insert is False
    assert can_update is False
    assert can_delete is False
