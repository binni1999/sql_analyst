from database.service import DatabaseService
from security.executor import SecureSQLExecutor
from security.guardrails import SQLSecurityGuardrail
from security.policies import SQLSecurityPolicy


class SQLExecutor:

    def __init__(
        self,
        db: DatabaseService,
        secure_executor: SecureSQLExecutor | None = None,
    ):

        self.db = db
        # Step 67.6: every production SQL execution must pass through the
        # security boundary. Build a secure executor when callers provide a
        # real DatabaseService but no explicit executor; never fall back to
        # DatabaseService.execute_query().
        self.secure_executor = secure_executor or SecureSQLExecutor(
            db=db,
            guardrail=SQLSecurityGuardrail(SQLSecurityPolicy()),
        )

    def execute(self, sql: str):

        print("\nEXECUTING SQL")
        print("=" * 60)
        print(sql)

        try:

            result = self.secure_executor.execute(sql)

            print("\nSQL EXECUTION SUCCESSFUL")

            print(
                f"Rows returned: "
                f"{len(result['rows'])}"
            )

            return {
                "success": True,
                "columns": result["columns"],
                "rows": result["rows"],
                "error": None
            }

        except Exception as e:

            print("\nSQL EXECUTION FAILED")

            print(
                f"Error: {str(e)}"
            )

            return {
                "success": False,
                "columns": [],
                "rows": [],
                "error": str(e)
            }