# pyrefly: ignore [missing-import]
from agents.answer_generator import AnswerGenerator


def main():

    question = "What are the top 5 products by revenue?"

    analyzed_result = {
        "row_count": 5,

        "columns": [
            "product_id",
            "product_name",
            "revenue"
        ],

        "data": [
            {
                "product_id": 3,
                "product_name": "Laptop",
                "revenue": 250000
            },
            {
                "product_id": 7,
                "product_name": "Phone",
                "revenue": 180000
            },
            {
                "product_id": 2,
                "product_name": "Monitor",
                "revenue": 120000
            },
            {
                "product_id": 5,
                "product_name": "Keyboard",
                "revenue": 90000
            },
            {
                "product_id": 8,
                "product_name": "Mouse",
                "revenue": 70000
            }
        ],

        "is_empty": False
    }

    generator = AnswerGenerator()

    answer = generator.generate(
        question,
        analyzed_result
    )

    print("\nFINAL ANSWER")
    print("=" * 60)
    print(answer)


if __name__ == "__main__":
    main()