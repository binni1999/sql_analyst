from models.conversation import ConversationState


class FollowUpResolver:

    METRIC_REPLACEMENTS = {
        "revenue": "revenue",
        "sales": "revenue",
        "quantity": "quantity",
        "units": "quantity",
        "units sold": "quantity",
        "rating": "rating",
        "reviews": "reviews",
    }

    SORT_REPLACEMENTS = {
        "ascending": "ascending",
        "asc": "ascending",
        "lowest first": "ascending",
        "smallest first": "ascending",
        "descending": "descending",
        "desc": "descending",
        "highest first": "descending",
        "largest first": "descending",
    }

    def resolve(
        self,
        conversation: ConversationState,
        user_question: str
    ) -> str:

        question = user_question.strip()

        if not question:
            raise ValueError(
                "Follow-up question cannot be empty."
            )

        # Prefer the explicit conversation fields for backward
        # compatibility. Structured memory is the fallback source of truth
        # introduced in Step 63.
        previous_question = (
            conversation.resolved_question
            or conversation.original_question
            or (
                conversation.memory.recent_resolved_questions[-1]
                if conversation.memory.recent_resolved_questions
                else None
            )
        )

        if not previous_question:

            raise ValueError(
                "No previous question is available "
                "to resolve the follow-up."
            )

        normalized = question.lower()

        # ----------------------------------
        # 1. Metric follow-up
        # ----------------------------------

        metric = self._detect_metric(normalized)

        if metric:
            return self._replace_metric(
                previous_question,
                metric
            )

        # ----------------------------------
        # 2. Sorting follow-up
        # ----------------------------------

        sort_direction = self._detect_sort_direction(
            normalized
        )

        if sort_direction:
            return self._apply_sort(
                previous_question,
                sort_direction
            )

        # ----------------------------------
        # 3. Filter / time follow-up
        # ----------------------------------

        if self._is_filter_follow_up(normalized):

            return self._append_filter(
                previous_question,
                question
            )

        # ----------------------------------
        # 4. Generic contextual follow-up
        # ----------------------------------

        return self._combine_questions(
            previous_question,
            question
        )

    def _detect_metric(
        self,
        question: str
    ) -> str | None:

        # Check longer phrases first.
        candidates = sorted(
            self.METRIC_REPLACEMENTS.items(),
            key=lambda item: len(item[0]),
            reverse=True
        )

        for keyword, metric in candidates:

            if keyword in question:
                return metric

        return None

    def _replace_metric(
        self,
        previous_question: str,
        metric: str
    ) -> str:

        question = previous_question

        replacements = {
            "revenue": "quantity",
            "sales": "quantity",
            "quantity": "revenue",
            "units": "revenue",
            "rating": "revenue",
            "reviews": "revenue",
        }

        # We intentionally perform a limited replacement.
        #
        # This handles our current supported
        # conversational metric switching.
        for old, new in replacements.items():

            if old in question.lower():

                start = question.lower().index(old)

                end = start + len(old)

                question = (
                    question[:start]
                    + metric
                    + question[end:]
                )

                return question

        # If no metric exists in the previous
        # question, append the requested metric.

        return (
            f"{previous_question} "
            f"using {metric}"
        )

    def _detect_sort_direction(
        self,
        question: str
    ) -> str | None:

        for keyword, direction in (
            self.SORT_REPLACEMENTS.items()
        ):

            if keyword in question:

                return direction

        return None

    def _apply_sort(
        self,
        previous_question: str,
        direction: str
    ) -> str:

        if direction == "ascending":

            return (
                f"{previous_question} "
                "sorted in ascending order"
            )

        return (
            f"{previous_question} "
            "sorted in descending order"
        )

    def _is_filter_follow_up(
        self,
        question: str
    ) -> bool:

        filter_keywords = [
            "only",
            "for ",
            "in ",
            "from ",
            "during ",
            "between ",
            "after ",
            "before ",
            "where ",
        ]

        return any(
            keyword in question
            for keyword in filter_keywords
        )

    def _append_filter(
        self,
        previous_question: str,
        filter_text: str
    ) -> str:
        return f"{previous_question} with {filter_text.lower()}"

    def _combine_questions(
        self,
        previous_question: str,
        follow_up: str
    ) -> str:

        return (
            f"{previous_question}. "
            f"{follow_up}"
        )