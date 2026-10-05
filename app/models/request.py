from pydantic import BaseModel, Field


class DataAnalystRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description=(
            "Natural language question about "
            "the database"
        )
    )

    human_approval: bool | None = Field(
        default=None,
        description=(
            "Approval decision for a query paused by the human-in-the-loop risk check. "
            "True approves execution; False rejects it."
        ),
    )

    conversation_id: str | None = Field(
        default=None,
        description=(
            "Identifier used to maintain "
            "conversation state across requests"
        )
    )