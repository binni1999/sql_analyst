from models.conversation import ConversationState


class ClarificationResolver:

    OPTION_MAPPINGS = {
        "highest revenue": (
            "revenue"
        ),
        "most units sold": (
            "units"
        ),
        "highest customer rating": (
            "rating"
        )
    }

    def resolve(
        self,
        conversation: ConversationState,
        user_response: str
    ) -> str:

        response = (
            user_response
            .lower()
            .strip()
        )

        original = (
            conversation.original_question
            or ""
        )

        if response == "highest revenue":

            return (
                f"{original} "
                "ranked by highest revenue"
            )

        if response == "most units sold":

            return (
                f"{original} "
                "ranked by most units sold"
            )

        if response == "highest customer rating":

            return (
                f"{original} "
                "ranked by highest customer rating"
            )

        # Allow a direct metric response
        if "revenue" in response:

            return (
                f"{original} "
                "ranked by revenue"
            )

        if (
            "units" in response
            or "quantity" in response
        ):

            return (
                f"{original} "
                "ranked by units sold"
            )

        if "rating" in response:

            return (
                f"{original} "
                "ranked by customer rating"
            )

        raise ValueError(
            "Unable to resolve the clarification "
            "response."
        )