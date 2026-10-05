# pyrefly: ignore [missing-import]
from agents.result_analyzer import ResultAnalyzer


def main():

    # -----------------------------------------
    # Simulated database result
    # -----------------------------------------

    result = {
        "columns": [
            "product_id",
            "product_name",
            "revenue"
        ],

        "rows": [
            
        ]
    }

    # -----------------------------------------
    # Analyzer
    # -----------------------------------------

    analyzer = ResultAnalyzer()

    analyzed_result = analyzer.analyze(
        result
    )

    # -----------------------------------------
    # Print
    # -----------------------------------------

    print("\nANALYZED RESULT")
    print("=" * 60)

    print(
        f"Row count: "
        f"{analyzed_result['row_count']}"
    )

    print(
        f"Columns: "
        f"{analyzed_result['columns']}"
    )

    print(
        f"Is empty: "
        f"{analyzed_result['is_empty']}"
    )

    print("\nData:")

    for row in analyzed_result["data"]:

        print(row)


if __name__ == "__main__":
    main()