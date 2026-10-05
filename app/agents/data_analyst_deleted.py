from agents.sql_agent import SQLAgent
from agents.sql_executor import SQLExecutor
from agents.result_analyzer import ResultAnalyzer
from agents.answer_generator import AnswerGenerator

from database.service import DatabaseService
from database.metadata_service import MetadataService


class DataAnalystAgent_Bkp:

    def __init__(
        self,
        sql_agent: SQLAgent,
        sql_executor: SQLExecutor,
        result_analyzer: ResultAnalyzer,
        answer_generator: AnswerGenerator,
        db: DatabaseService,
        metadata_service: MetadataService
    ):

        self.sql_agent = sql_agent
        self.sql_executor = sql_executor
        self.result_analyzer = result_analyzer
        self.answer_generator = answer_generator
        self.db = db
        self.metadata_service = metadata_service

    def build_schema_text(self, schemas: list[dict]):

        schema_text = ""

        for schema in schemas:

            schema_text += f"\nTABLE {schema['table']}\n"

            schema_text += "\nColumns:\n"

            for column in schema["columns"]:

                schema_text += (
                    f"- {column['name']} {column['type']}\n"
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

    def ask(self, question: str):

        print("\n" + "=" * 70)
        print("DATA ANALYST AGENT")
        print("=" * 70)

        print("\nUser Question:")
        print(question)

        print("\nFetching database schema...")

        schemas = self.db.get_full_schema()

        schema_text = self.build_schema_text(
            schemas
        )

        print("\nFetching semantic metadata...")

        metadata_text = (
            self.metadata_service.build_metadata_text()
        )

        sql_result = self.sql_agent.generate_valid_sql(
            question=question,
            schema=schema_text,
            schemas=schemas,
            metadata=metadata_text
        )

        if not sql_result["success"]:

            return {
                "success": False,
                "question": question,
                "sql": sql_result.get("sql"),
                "answer": None,
                "error": sql_result.get("errors")
            }

        sql = sql_result["sql"]

        execution_result = self.sql_executor.execute(
            sql
        )

        if not execution_result["success"]:

            return {
                "success": False,
                "question": question,
                "sql": sql,
                "answer": None,
                "error": execution_result["error"]
            }

        analyzed_result = self.result_analyzer.analyze(
            execution_result
        )

        answer = self.answer_generator.generate(
            question=question,
            analyzed_result=analyzed_result
        )

        return {
            "success": True,
            "question": question,
            "sql": sql,
            "result": analyzed_result,
            "answer": answer,
            "error": None
        }