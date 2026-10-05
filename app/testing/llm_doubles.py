"""Deterministic LLM doubles used by the CI/test environment.

The production application uses Groq. CI must not depend on an external LLM
API, network availability, API quotas, or secrets, so test mode uses these
small deterministic implementations while keeping the real SQL validation,
security, execution, checkpointing, and conversation flow intact.
"""

from models.analytical_context import AnalyticalContext
from agents.sql_generator import SQLGenerationResult


class TestSQLGenerator:
    """Deterministic SQL generator for end-to-end CI tests."""

    llm = None

    def generate(
        self,
        question: str,
        schema: str,
        metadata: str,
        analytical_context: AnalyticalContext | None = None,
        business_knowledge=None,
    ) -> SQLGenerationResult:
        normalized = question.lower()

        if "quantity" in normalized or "units" in normalized:
            sql = """
SELECT
    p.product_name,
    SUM(oi.quantity) AS total_quantity
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_quantity DESC
LIMIT 5
""".strip()
            return SQLGenerationResult(
                sql=sql,
                tables_used=["products", "order_items"],
                metrics_used=["quantity"],
                explanation="Ranks the top 5 products by total quantity sold.",
            )

        sql = """
SELECT
    p.product_name,
    SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS total_revenue
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_revenue DESC
LIMIT 5
""".strip()
        return SQLGenerationResult(
            sql=sql,
            tables_used=["products", "order_items"],
            metrics_used=["revenue"],
            explanation="Ranks the top 5 products by revenue after discount.",
        )

    def fix_sql(
        self,
        question: str,
        sql: str,
        errors: list[str],
        schema: str,
        metadata: str,
        analytical_context: AnalyticalContext | None = None,
        business_knowledge=None,
    ) -> str:
        # The deterministic initial SQL is intentionally valid. Returning it
        # also gives the repair path a safe deterministic fallback in tests.
        return self.generate(
            question=question,
            schema=schema,
            metadata=metadata,
            analytical_context=analytical_context,
            business_knowledge=business_knowledge,
        ).sql


class TestAnswerGenerator:
    """Deterministic answer generator for end-to-end CI tests."""

    def generate(self, question: str, analyzed_result: dict) -> str:
        row_count = analyzed_result.get("row_count", 0)
        if row_count == 0:
            return "No data was found for the requested question."
        return (
            f"Found {row_count} result rows for the requested analysis."
        )
