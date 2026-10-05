from concurrent.futures import ThreadPoolExecutor

from models.agent import MetadataResult
from models.execution_trace import ExecutionTraceEvent
from models.state import AgentState


class MetadataAgent:

    SCHEMA_CACHE_KEY = "datapilot:metadata:schema:v1"

    def __init__(self, metadata_service, db, cache_service=None):
        self.metadata_service = metadata_service
        self.db = db
        self.cache_service = cache_service

    def build_schema_text(self, schemas):

        schema_text = ""

        for schema in schemas:

            schema_text += (
                f"\nTABLE {schema['table']}\n"
            )

            schema_text += "\nColumns:\n"

            for column in schema["columns"]:

                schema_text += (
                    f"- {column['name']} "
                    f"{column['type']}\n"
                )

            if schema["primary_keys"]:

                schema_text += "\nPrimary Keys:\n"

                for pk in schema["primary_keys"]:
                    schema_text += f"- {pk}\n"

            if schema["foreign_keys"]:

                schema_text += "\nForeign Keys:\n"

                for fk in schema["foreign_keys"]:

                    schema_text += (
                        f"- {fk['column']} → "
                        f"{fk['references_table']}."
                        f"{fk['references_column']}\n"
                    )

        return schema_text

    def _add_trace_event(
        self,
        state: AgentState,
        *,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
        error_type: str | None = None,
    ):
        event = ExecutionTraceEvent(
            stage="metadata",
            status=status,
            attempt=0,
            message=message,
            error_type=error_type,
            metadata=metadata or {},
        )
        state.execution_trace.append(
            event.model_dump(exclude_none=True)
        )

    def _retrieve_schema(self):
        """Retrieve database schema, using Redis when available."""
        if self.cache_service is not None:
            cached = self.cache_service.get_json(self.SCHEMA_CACHE_KEY)
            if cached is not None:
                return cached["schemas"], cached["schema_text"]

        schemas = self.db.get_full_schema()
        schema_text = self.build_schema_text(schemas)

        if self.cache_service is not None:
            self.cache_service.set_json(
                self.SCHEMA_CACHE_KEY,
                {"schemas": schemas, "schema_text": schema_text},
            )

        return schemas, schema_text

    def _retrieve_business_metadata(self):
        """Retrieve semantic/business metadata independently of schema."""
        return self.metadata_service.build_metadata_text()

    def run(self, state: AgentState):

        self._add_trace_event(
            state,
            status="started",
            message="Metadata retrieval started.",
            metadata={
                "component": self.__class__.__name__,
                "parallel_branches": [
                    "schema_retrieval",
                    "business_metadata_retrieval",
                ],
            },
        )

        print("\n" + "-" * 60)
        print("METADATA AGENT")
        print("-" * 60)

        try:
            # These operations are independent: schema retrieval reads
            # PostgreSQL metadata, while business metadata is read from
            # the in-process MetadataService. Running them concurrently
            # reduces the metadata stage latency without changing the
            # downstream contract consumed by SQLAgent.
            with ThreadPoolExecutor(max_workers=2) as executor:
                schema_future = executor.submit(
                    self._retrieve_schema
                )
                business_metadata_future = executor.submit(
                    self._retrieve_business_metadata
                )

                schemas, schema_text = schema_future.result()
                metadata = business_metadata_future.result()

            metadata_result = MetadataResult(
                schemas=schemas,
                schema_text=schema_text,
                metadata=metadata,
            )

            state.metadata = metadata_result

            state.mark_success()

            self._add_trace_event(
                state,
                status="success",
                message="Schema and semantic metadata retrieved successfully in parallel.",
                metadata={
                    "component": self.__class__.__name__,
                    "table_count": len(schemas),
                    "metadata_available": bool(metadata),
                    "parallel_branches_completed": 2,
                },
            )

            return state

        except Exception as exc:
            self._add_trace_event(
                state,
                status="failed",
                message="Metadata retrieval failed.",
                error_type="metadata",
                metadata={
                    "component": self.__class__.__name__,
                    "exception_type": type(exc).__name__,
                },
            )
            raise
