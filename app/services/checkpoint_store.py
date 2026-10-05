from __future__ import annotations

import atexit
import os

from langgraph.checkpoint.postgres import PostgresSaver


class PostgresCheckpointStore:
    """Own the lifetime of the LangGraph PostgreSQL checkpointer."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv(
            "LANGGRAPH_CHECKPOINT_DB_URL",
            "postgresql://postgres:root123@localhost:5432/datapilot",
        )
        self._context = PostgresSaver.from_conn_string(self.database_url)
        self.checkpointer = self._context.__enter__()
        self.checkpointer.setup()
        atexit.register(self.close)

    def close(self) -> None:
        context = self._context
        if context is not None:
            self._context = None
            context.__exit__(None, None, None)
