from models.business_knowledge import BusinessKnowledgeDocument


BUSINESS_KNOWLEDGE_DOCUMENTS = [
    BusinessKnowledgeDocument(
        document_id="metric.revenue",
        title="Revenue",
        content=(
            "Revenue is the total sales value after applying the discount. "
            "It is calculated as "
            "SUM(quantity * unit_price * (1 - discount)) "
            "from order_items."
        ),
        source=(
            "database.metadata.METRIC_METADATA.revenue"
        ),
        metadata={
            "metric": "revenue",
            "tables": ["order_items"],
            "required_columns": [
                "quantity",
                "unit_price",
                "discount",
            ],
        },
        keywords=[
            "revenue",
            "sales",
            "sales value",
            "total sales",
            "discount",
            "unit price",
            "quantity",
        ],
    ),

    BusinessKnowledgeDocument(
        document_id="metric.quantity",
        title="Quantity Sold",
        content=(
            "Quantity represents the total number of units purchased. "
            "It is calculated as SUM(quantity) "
            "from order_items."
        ),
        source=(
            "database.metadata.METRIC_METADATA.quantity"
        ),
        metadata={
            "metric": "quantity",
            "tables": ["order_items"],
            "required_columns": [
                "quantity",
            ],
        },
        keywords=[
            "quantity",
            "units",
            "units sold",
            "number of units",
        ],
    ),
]