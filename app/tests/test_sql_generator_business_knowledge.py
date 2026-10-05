# pyrefly: ignore [missing-import]
from agents.sql_generator import SQLGenerator
from models.business_knowledge import (
    BusinessKnowledgeDocument,
    BusinessKnowledgeMatch,
    BusinessKnowledgeResult,
)


def _knowledge():
    document = BusinessKnowledgeDocument(
        document_id="metric.revenue",
        title="Revenue",
        content=(
            "Revenue is total sales after discount. "
            "Formula: SUM(quantity * unit_price * (1 - discount))."
        ),
        source="test",
        metadata={
            "metric": "revenue",
            "tables": ["order_items"],
            "required_columns": ["quantity", "unit_price", "discount"],
        },
        keywords=["revenue", "sales"],
    )
    return BusinessKnowledgeResult(
        query="top products by revenue",
        matches=[
            BusinessKnowledgeMatch(
                document=document,
                score=1.0,
                matched_keywords=["revenue"],
            )
        ],
    )


def test_generate_includes_business_knowledge():
    generator = SQLGenerator.__new__(SQLGenerator)
    captured = {}

    class FakeStructuredLLM:
        def invoke(self, messages):
            captured["messages"] = messages
            return None

    generator.structured_llm = FakeStructuredLLM()

    generator.generate(
        question="Show top products by revenue",
        schema="products(id, name)",
        metadata="revenue = SUM(...)" ,
        business_knowledge=_knowledge(),
    )

    prompt = captured["messages"][1][1]
    assert "BUSINESS KNOWLEDGE CONTEXT" in prompt
    assert "metric.revenue" in prompt
    assert "SUM(quantity * unit_price * (1 - discount))" in prompt
    assert "order_items" in prompt


def test_fix_sql_includes_business_knowledge():
    generator = SQLGenerator.__new__(SQLGenerator)
    captured = {}

    class FakeLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            class Response:
                content = "SELECT 1"
            return Response()

    generator.llm = FakeLLM()

    generator.fix_sql(
        question="Show top products by revenue",
        sql="SELECT invalid",
        errors=["Invalid column"],
        schema="products(id, name)",
        metadata="revenue = SUM(...)",
        business_knowledge=_knowledge(),
    )

    prompt = captured["prompt"]
    assert "Business Knowledge Context:" in prompt
    assert "metric.revenue" in prompt
    assert "SUM(quantity * unit_price * (1 - discount))" in prompt
