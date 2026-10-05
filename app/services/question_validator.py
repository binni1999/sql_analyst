class QuestionValidator:

    def validate(self, question: str):

        errors = []

        if not question:
            errors.append("Question cannot be empty.")

        question = question.strip()

        if len(question) < 3:
            errors.append(
                "Question must contain at least 3 characters."
            )

        if len(question) > 1000:
            errors.append(
                "Question cannot exceed 1000 characters."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }