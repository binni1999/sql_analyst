from factory import create_data_analyst_service
from models.request import DataAnalystRequest


def main():

    service = create_data_analyst_service()

    request = DataAnalystRequest(
        question="Hi"
    )

    response = service.ask(request)

    print("\n" + "=" * 70)
    print("FINAL RESPONSE")
    print("=" * 70)

    print("\nAnswer:")
    print(response.answer)

    print("\nGenerated SQL:")
    print(response.sql)

    print("\nSuccess:")
    print(response.success)

    print("\nStructured Response:")
    print(response.model_dump())


if __name__ == "__main__":
    main()