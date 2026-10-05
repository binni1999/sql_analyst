from agents.sql_generator import SQLGenerator
from models.analytical_context import AnalyticalContext


def test_generate_includes_analytical_context():

    generator = SQLGenerator.__new__(SQLGenerator)

    captured = {}

    class FakeStructuredLLM:

        def invoke(self, messages):
            captured["messages"] = messages
            return None

    generator.structured_llm = FakeStructuredLLM()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc",
        time_range={
            "type": "month",
            "year": 2025,
            "month": 1,
            "start": "2025-01-01",
            "end": "2025-01-31"
        }
    )

    generator.generate(
        question="Show top 5 products by revenue in January 2025",
        schema="products(id, name)",
        metadata=(
            "revenue = "
            "SUM(quantity * unit_price * (1 - discount))"
        ),
        analytical_context=context
    )

    human_prompt = captured["messages"][1][1]

    assert "STRUCTURED ANALYTICAL CONTEXT" in human_prompt
    assert '"entity": "product"' in human_prompt
    assert '"metric": "revenue"' in human_prompt
    assert '"aggregation": "sum"' in human_prompt
    assert '"limit": 5' in human_prompt
    assert '"sort_direction": "desc"' in human_prompt
    assert '"year": 2025' in human_prompt
    assert '"month": 1' in human_prompt


def test_generate_without_analytical_context():

    generator = SQLGenerator.__new__(SQLGenerator)

    captured = {}

    class FakeStructuredLLM:

        def invoke(self, messages):
            captured["messages"] = messages
            return None

    generator.structured_llm = FakeStructuredLLM()

    generator.generate(
        question="Show total revenue",
        schema="order_items(quantity, unit_price, discount)",
        metadata=(
            "revenue = "
            "SUM(quantity * unit_price * (1 - discount))"
        )
    )

    human_prompt = captured["messages"][1][1]

    assert "STRUCTURED ANALYTICAL CONTEXT" in human_prompt
    assert (
        "No structured analytical context is available."
        in human_prompt
    )


def test_fix_sql_includes_analytical_context():

    generator = SQLGenerator.__new__(SQLGenerator)

    captured = {}

    class FakeLLM:

        def invoke(self, prompt):
            captured["prompt"] = prompt

            class Response:
                content = "SELECT 1"

            return Response()

    generator.llm = FakeLLM()

    context = AnalyticalContext(
        entity="product",
        metric="revenue",
        aggregation="sum",
        limit=5,
        sort_direction="desc"
    )

    generator.fix_sql(
        question="Show top 5 products by revenue",
        sql="SELECT invalid",
        errors=["Invalid column"],
        schema="products(id, name)",
        metadata="revenue = SUM(...)",
        analytical_context=context
    )

    prompt = captured["prompt"]

    assert "Structured Analytical Context:" in prompt
    assert '"entity": "product"' in prompt
    assert '"metric": "revenue"' in prompt
    assert '"limit": 5' in prompt
    assert (
        "Respect the structured analytical context"
        in prompt
    )