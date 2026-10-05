import sys
from pathlib import Path
import os 
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
)

# Ensure project root and app directory are in sys.path
_file_path = Path(__file__).resolve()
_app_dir = _file_path.parent.parent
_root_dir = _app_dir.parent

if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from database.service import DatabaseService



def build_schema_text(db: DatabaseService):

    tables = db.get_tables()

    schema_parts = []

    for table in tables:

        schema_parts.append(
            f"\nTABLE: {table}"
        )

        columns = db.get_schema(table)

        for column in columns:

            schema_parts.append(
                f"  - {column['column_name']}"
                f" ({column['data_type']})"
            )

    return "\n".join(schema_parts)

# pyrefly: ignore [name-defined]
db = DatabaseService()
schema = build_schema_text(db)



SYSTEM_PROMPT = """
You are an expert PostgreSQL data analyst.

Your job is to convert a natural language
question into a PostgreSQL SQL query.

You have access to the database schema provided
by the user.

Rules:

1. Only use tables present in the schema.
2. Only use columns present in the schema.
3. Never invent tables or columns.
4. Only generate SELECT or WITH queries.
5. Never generate INSERT.
6. Never generate UPDATE.
7. Never generate DELETE.
8. Never generate DROP.
9. Never generate ALTER.
10. Never generate TRUNCATE.
11. Use appropriate JOIN conditions.
12. Use GROUP BY when required.
13. Use ORDER BY when appropriate.
14. Return ONLY the SQL query.
"""

def generate_sql(
    question: str,
    schema: str
):

    prompt = f"""
{SYSTEM_PROMPT}

DATABASE SCHEMA:

{schema}

USER QUESTION:

{question}

Generate the PostgreSQL query.
"""

    response = llm.invoke(prompt)

    return response.content



question = """
What are the top 5 products by revenue?
"""

sql = generate_sql(
    question,
    schema
)

print(sql)