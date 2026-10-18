from fastapi import APIRouter, Depends, HTTPException, Request

from models.request import DataAnalystRequest
from models.response import DataAnalystResponse
from factory import create_data_analyst_service
try:
    from services.auth_service import current_user, owns_conversation, claim_conversation
except ImportError:
    from app.services.auth_service import current_user, owns_conversation, claim_conversation


router = APIRouter(
    prefix="/api",
    tags=["Data Analyst"]
)


service = create_data_analyst_service()


@router.post(
    "/ask",
    response_model=DataAnalystResponse
)
def ask_data_analyst(
    request: DataAnalystRequest,
    user: dict = Depends(current_user),
):
    # Conversation identifiers are private to the authenticated owner.
    if request.conversation_id and not owns_conversation(user["id"], request.conversation_id):
        raise HTTPException(status_code=403, detail="Conversation not found or not accessible")
    response = service.ask(request)
    claim_conversation(user["id"], response.conversation_id)
    return response