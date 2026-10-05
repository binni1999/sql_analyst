from datetime import date, timedelta
import re

from models.analytical_context import AnalyticalContext


class AnalyticalContextExtractor:

    METRIC_MAPPINGS = {
        "revenue": "revenue",
        "sales": "revenue",
        "sales value": "revenue",

        "quantity": "quantity",
        "units": "quantity",
        "units sold": "quantity",

        "rating": "rating",
        "ratings": "rating",

        "reviews": "reviews",
    }

    ENTITY_MAPPINGS = {
        "product": "product",
        "products": "product",

        "customer": "customer",
        "customers": "customer",

        "order": "order",
        "orders": "order",
    }

    # ============================================================
    # PUBLIC API
    # ============================================================

    def extract(
        self,
        question: str,
        previous_context: AnalyticalContext | None = None
    ) -> AnalyticalContext:

        normalized = question.strip().lower()

        if previous_context is not None:
            context = previous_context.model_copy(
                deep=True
            )
        else:
            context = AnalyticalContext()

        # --------------------------------------------------------
        # Entity
        # --------------------------------------------------------

        entity = self._extract_entity(normalized)

        if entity:
            context.entity = entity

        # --------------------------------------------------------
        # Metric
        # --------------------------------------------------------

        metric = self._extract_metric(normalized)

        if metric:
            context.metric = metric

        # --------------------------------------------------------
        # Aggregation
        # --------------------------------------------------------

        aggregation = self._extract_aggregation(
            normalized,
            context.metric
        )

        if aggregation:
            context.aggregation = aggregation

        # --------------------------------------------------------
        # Limit
        # --------------------------------------------------------

        limit = self._extract_limit(normalized)

        if limit is not None:
            context.limit = limit

        # --------------------------------------------------------
        # Sort direction
        # --------------------------------------------------------

        sort_direction = self._extract_sort_direction(
            normalized
        )

        if sort_direction:
            context.sort_direction = sort_direction

        # --------------------------------------------------------
        # Filters
        # --------------------------------------------------------

        filters = self._extract_filters(normalized)

        if filters:
            context.filters = self._merge_filters(
                context.filters,
                filters
            )

        # --------------------------------------------------------
        # Time range
        # --------------------------------------------------------

        time_range = self._extract_time_range(
            normalized
        )

        if time_range:
            context.time_range = time_range

        return context

    # ============================================================
    # ENTITY
    # ============================================================

    def _extract_entity(
        self,
        question: str
    ) -> str | None:

        candidates = sorted(
            self.ENTITY_MAPPINGS.items(),
            key=lambda item: len(item[0]),
            reverse=True
        )

        for keyword, entity in candidates:

            if self._contains_phrase(
                question,
                keyword
            ):
                return entity

        return None

    # ============================================================
    # METRIC
    # ============================================================

    def _extract_metric(
        self,
        question: str
    ) -> str | None:

        candidates = sorted(
            self.METRIC_MAPPINGS.items(),
            key=lambda item: len(item[0]),
            reverse=True
        )

        for keyword, metric in candidates:

            if self._contains_phrase(
                question,
                keyword
            ):
                return metric

        return None

    # ============================================================
    # AGGREGATION
    # ============================================================

    def _extract_aggregation(
        self,
        question: str,
        metric: str | None
    ) -> str | None:

        # Explicit aggregation takes precedence.

        if any(
            phrase in question
            for phrase in [
                "average",
                "avg",
                "mean",
            ]
        ):
            return "avg"

        if any(
            phrase in question
            for phrase in [
                "count",
                "number of",
                "how many",
            ]
        ):
            return "count"

        if any(
            phrase in question
            for phrase in [
                "maximum",
                "maximum value",
                "max",
                "highest",
        ]):
            return "max"

        if any(
            phrase in question
            for phrase in [
                "minimum",
                "minimum value",
                "min",
                "lowest",
        ]):
            return "min"

        if metric in {
            "revenue",
            "quantity",
        }:
            return "sum"

        if metric == "rating":
            return "avg"

        if metric == "reviews":
            return "count"

        return None

    # ============================================================
    # LIMIT
    # ============================================================

    def _extract_limit(
        self,
        question: str
    ) -> int | None:

        patterns = [
            r"\btop\s+(\d+)\b",
            r"\bbottom\s+(\d+)\b",
            r"\bfirst\s+(\d+)\b",
            r"\blast\s+(\d+)\b",
            r"\b(\d+)\s+(?:best|worst)\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                question
            )

            if match:
                return int(match.group(1))

        return None

    # ============================================================
    # SORT DIRECTION
    # ============================================================

    def _extract_sort_direction(
        self,
        question: str
    ) -> str | None:

        descending_phrases = [
            "descending",
            "desc",
            "highest first",
            "largest first",
            "top",
            "best",
            "most",
        ]

        ascending_phrases = [
            "ascending",
            "asc",
            "lowest first",
            "smallest first",
            "bottom",
            "worst",
            "least",
        ]

        if any(
            phrase in question
            for phrase in descending_phrases
        ):
            return "descending"

        if any(
            phrase in question
            for phrase in ascending_phrases
        ):
            return "ascending"

        return None

    # ============================================================
    # TIME RANGE
    # ============================================================

    def _extract_time_range(
        self,
        question: str
    ) -> dict | None:

    # --------------------------------------------------------
    # Month + year
    #
    # IMPORTANT:
    # This must be checked BEFORE the generic year pattern.
    #
    # Example:
    #   January 2025
    #
    # should produce:
    #   type = month
    #   year = 2025
    #   month = 1
    # --------------------------------------------------------

        month_match = re.search(
        r"\b("
        r"january|february|march|april|may|june|"
        r"july|august|september|october|november|december"
        r")\s+(20\d{2})\b",
        question
    )

        if month_match:

            month_name = month_match.group(1)
            year = int(
                month_match.group(2)
            )

            month_numbers = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
            }

            month = month_numbers[
                month_name
            ]

            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year

            first_day = date(
                year,
                month,
                1
            )

            first_day_next_month = date(
                next_year,
                next_month,
                1
            )

            last_day = (
                first_day_next_month
                - timedelta(days=1)
            )

            return {
            "type": "month",
            "year": year,
            "month": month,
            "start": first_day.isoformat(),
            "end": last_day.isoformat(),
            }

    # --------------------------------------------------------
    # Explicit year
    #
    # Example:
    #   revenue in 2025
    # --------------------------------------------------------

        year_match = re.search(
            r"\b(20\d{2})\b",
            question
        )

        if year_match:

            year = int(
                year_match.group(1)
            )

            return {
                "type": "year",
                "year": year,
                "start": f"{year}-01-01",
                "end": f"{year}-12-31",
            }

    # --------------------------------------------------------
    # This year
    # --------------------------------------------------------

        if re.search(
            r"\bthis year\b",
            question
        ):

            year = date.today().year

            return {
                "type": "year",
                "year": year,
                "start": f"{year}-01-01",
                "end": f"{year}-12-31",
            }

    # --------------------------------------------------------
    # Last year
    # --------------------------------------------------------

        if re.search(
            r"\blast year\b",
            question
        ):

            year = date.today().year - 1

            return {
                "type": "year",
                "year": year,
                "start": f"{year}-01-01",
                "end": f"{year}-12-31",
            }

        return None
    # ============================================================
    # FILTERS
    # ============================================================

    def _extract_filters(
        self,
        question: str
    ) -> list[dict]:

        filters = []

        # --------------------------------------------------------
        # customers from/in <location>
        # --------------------------------------------------------

        customer_location = re.search(
            r"\bcustomers?\s+"
            r"(?:from|in)\s+"
            r"([a-z][a-z\s-]*?)"
            r"(?:\s+and\s+|\s+with\s+|\s+having\s+|$)",
            question
        )

        if customer_location:

            location = (
                customer_location
                .group(1)
                .strip()
            )

            if location:

                filters.append(
                    {
                        "field": "customer.city",
                        "operator": "=",
                        "value": self._clean_value(
                            location
                        ),
                    }
                )

        # --------------------------------------------------------
        # city is <location>
        # --------------------------------------------------------

        city_match = re.search(
            r"\bcity\s+is\s+"
            r"([a-z][a-z\s-]*?)"
            r"(?:\s+and\s+|\s+with\s+|\s+having\s+|$)",
            question
        )

        if city_match:

            city = (
                city_match
                .group(1)
                .strip()
            )

            if city:

                filters.append(
                    {
                        "field": "city",
                        "operator": "=",
                        "value": self._clean_value(
                            city
                        ),
                    }
                )

        # --------------------------------------------------------
        # Generic "in <location>"
        #
        # Example:
        #   revenue in delhi
        # --------------------------------------------------------

        generic_location = re.search(
            r"\bin\s+"
            r"([a-z][a-z\s-]*?)"
            r"(?:\s+in\s+\d{4}"
            r"|\s+and\s+"
            r"|\s+with\s+"
            r"|$)",
            question
        )

        if (
            generic_location
            and not customer_location
        ):

            location = (
                generic_location
                .group(1)
                .strip()
            )

            # Avoid treating "in 2025" as a location.

            if (
                location
                and not re.fullmatch(
                    r"20\d{2}",
                    location
                )
            ):

                filters.append(
                    {
                        "field": "city",
                        "operator": "=",
                        "value": self._clean_value(
                            location
                        ),
                    }
                )

        return filters

    # ============================================================
    # FILTER HELPERS
    # ============================================================

    def _merge_filters(
        self,
        existing: list[dict],
        new_filters: list[dict]
    ) -> list[dict]:

        result = [
            dict(item)
            for item in existing
        ]

        for new_filter in new_filters:

            already_exists = any(
                existing_filter == new_filter
                for existing_filter in result
            )

            if not already_exists:
                result.append(
                    new_filter
                )

        return result

    def _clean_value(
        self,
        value: str
    ) -> str:

        return value.strip(
            " ,."
        )

    # ============================================================
    # TEXT HELPERS
    # ============================================================

    def _contains_phrase(
        self,
        question: str,
        phrase: str
    ) -> bool:

        escaped = re.escape(
            phrase
        )

        return bool(
            re.search(
                rf"\b{escaped}\b",
                question
            )
        )