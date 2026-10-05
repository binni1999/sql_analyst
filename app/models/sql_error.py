from enum import Enum

from pydantic import BaseModel


class SQLErrorType(str, Enum):
    SYNTAX = "syntax"
    DATABASE = "database"
    SEMANTIC = "semantic"
    CONTEXT = "context"


class SQLError(BaseModel):
    error_type: SQLErrorType
    message: str
    source: str