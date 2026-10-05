from models.analytical_context import AnalyticalContext
from models.sql_requirements import SQLRequirements


class SQLRequirementsBuilder:
    """
    Converts structured AnalyticalContext into deterministic
    requirements that generated SQL must satisfy.
    """

    ENTITY_COLUMN_CANDIDATES = {
        "product": [
            "product_id",
            "product_name",
            "name",
        ],
        "customer": [
            "customer_id",
            "customer_name",
            "name",
        ],
        "order": [
            "order_id",
        ],
    }

    def build(
        self,
        analytical_context: AnalyticalContext | None,
    ) -> SQLRequirements:

        if analytical_context is None:
            return SQLRequirements()

        entity = analytical_context.entity

        group_by_required = entity is not None

        return SQLRequirements(
            metric=analytical_context.metric,
            aggregation=analytical_context.aggregation,
            entity=entity,
            group_by_required=group_by_required,
            filters=list(analytical_context.filters),
            time_range=(
                dict(analytical_context.time_range)
                if analytical_context.time_range
                else None
            ),
            time_range_required=(
                analytical_context.time_range is not None
            ),
            sort_direction=analytical_context.sort_direction,
            limit=analytical_context.limit,
        )

    def get_entity_column_candidates(
        self,
        entity: str | None,
    ) -> list[str]:

        if entity is None:
            return []

        return list(
            self.ENTITY_COLUMN_CANDIDATES.get(
                entity.lower(),
                []
            )
        )