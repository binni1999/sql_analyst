from enum import Enum


class QuestionIntent(str, Enum):
    DATA_QUERY = "data_query"
    UNKNOWN = "unknown"