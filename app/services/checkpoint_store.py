from __future__ import annotations

import atexit
from langgraph.checkpoint.postgres import PostgresSaver

try:
    from config import get_settings
except ImportError:
    from app.config import get_settings


class PostgresCheckpointStore:
    """Own the lifetime of the LangGraph PostgreSQL checkpointer."""

    def __init__(self, database_url: str | None = None):
        # Use the validated application settings instead of a hard-coded
        # database credential. A dedicated checkpoint URL remains optional.
        configured_url = database_url or get_settings().database_checkpoint_url
        # SQLAlchemy URLs may name a driver (e.g. postgresql+psycopg2),
        # whereas LangGraph's PostgresSaver uses psycopg connection strings.
        self.database_url = configured_url.replace(
            "postgresql+psycopg2://", "postgresql://", 1
        ).replace("postgresql+psycopg://", "postgresql://", 1)
        self._context = PostgresSaver.from_conn_string(self.database_url)
        self.checkpointer = self._context.__enter__()
        self.checkpointer.setup()
        atexit.register(self.close)

    def close(self) -> None:
        context = self._context
        if context is not None:
            self._context = None
            context.__exit__(None, None, None)
