from unittest.mock import MagicMock, patch

from agents.answer_generator import AnswerGenerator
from agents.sql_generator import SQLGenerator


@patch("agents.sql_generator.ChatGroq")
def test_sql_generator_disables_provider_retries(mock_chat_groq):
    mock_llm = MagicMock()
    mock_chat_groq.return_value = mock_llm

    SQLGenerator()

    kwargs = mock_chat_groq.call_args.kwargs
    assert kwargs["max_retries"] == 0
    assert len(kwargs["callbacks"]) == 1


@patch("agents.answer_generator.ChatGroq")
def test_answer_generator_disables_provider_retries(mock_chat_groq):
    mock_chat_groq.return_value = MagicMock()

    AnswerGenerator()

    kwargs = mock_chat_groq.call_args.kwargs
    assert kwargs["max_retries"] == 0
    assert len(kwargs["callbacks"]) == 1




@patch("agents.answer_generator.ChatGroq")
def test_answer_generator_preserves_valid_unicode(mock_chat_groq):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = (
        "Top product: Smartphone — $5,326.65"
    )
    mock_chat_groq.return_value = mock_llm

    generator = AnswerGenerator()
    answer = generator.generate(
        "Show the top product by revenue",
        {
            "row_count": 1,
            "columns": ["product_name", "revenue"],
            "data": [
                {
                    "product_name": "Smartphone",
                    "revenue": 5326.65,
                }
            ],
            "is_empty": False,
        },
    )

    assert "Smartphone" in answer
    assert "$5,326.65" in answer
    assert "—" in answer
    assert "â" not in answer
