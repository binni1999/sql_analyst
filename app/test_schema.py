import sys
from pathlib import Path

# Ensure project root and app directory are in sys.path
_file_path = Path(__file__).resolve()
_app_dir = _file_path.parent
_root_dir = _app_dir.parent

if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

try:
    from database.service import DatabaseService
    from database.schema_formatter import (
        format_database_schema_for_llm
    )
except ModuleNotFoundError:
    from app.database.service import DatabaseService
    from app.database.schema_formatter import (
        format_database_schema_for_llm
    )



db = DatabaseService()


schemas = db.get_full_schema()


schema_text = format_database_schema_for_llm(
    schemas
)


print(schema_text)