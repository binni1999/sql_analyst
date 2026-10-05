from fastapi import APIRouter

from models.request import DataAnalystRequest
from models.response import DataAnalystResponse
from factory import create_data_analyst_service


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
    request: DataAnalystRequest
):

    response = service.ask(request)

    return response