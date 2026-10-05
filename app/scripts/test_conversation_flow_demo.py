import sys
from pathlib import Path

# Add the app directory to Python's import path.
APP_DIR = Path(__file__).resolve().parent.parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


from factory import create_data_analyst_service
from models.request import DataAnalystRequest


def main():

    service = create_data_analyst_service()

    # ==========================================
    # TURN 1
    # ==========================================

    request_1 = DataAnalystRequest(
        question="Show the top 5 products by revenue"
    )

    response_1 = service.ask(request_1)

    print("\n" + "=" * 70)
    print("TURN 1")
    print("=" * 70)

    print("Conversation ID:")
    print(response_1.conversation_id)

    print("\nQuestion:")
    print(response_1.question)

    print("\nAnswer:")
    print(response_1.answer)

    print("\nSQL:")
    print(response_1.sql)

    print("\nSuccess:")
    print(response_1.success)

    if not response_1.success:
        print("\nError:")
        print(response_1.error)
        return

    # ==========================================
    # TURN 2
    # ==========================================

    request_2 = DataAnalystRequest(
        question="What about quantity?",
        conversation_id=response_1.conversation_id
    )

    response_2 = service.ask(request_2)

    print("\n" + "=" * 70)
    print("TURN 2")
    print("=" * 70)

    print("Conversation ID:")
    print(response_2.conversation_id)

    print("\nQuestion:")
    print(response_2.question)

    print("\nAnswer:")
    print(response_2.answer)

    print("\nSQL:")
    print(response_2.sql)

    print("\nSuccess:")
    print(response_2.success)

    if not response_2.success:
        print("\nError:")
        print(response_2.error)

    # ==========================================
    # VERIFY SAME CONVERSATION
    # ==========================================

    print("\n" + "=" * 70)
    print("CONVERSATION CHECK")
    print("=" * 70)

    print(
        "Same conversation:",
        response_1.conversation_id == response_2.conversation_id
    )

    # ==========================================
    # INSPECT HISTORY
    # ==========================================

    conversation = service.conversation_service.get(
        response_1.conversation_id
    )

    print("\nConversation history:")

    for message in conversation.history:
        print(
            f"{message['role'].upper()}: "
            f"{message['content']}"
        )

    print("\nResolved question:")
    print(conversation.resolved_question)


if __name__ == "__main__":
    main()