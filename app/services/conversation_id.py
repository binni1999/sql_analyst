import uuid


def generate_conversation_id() -> str:
    return str(uuid.uuid4())