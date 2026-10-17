# pyrefly: ignore [missing-import]

from pydantic import BaseModel, Field

import os

from dotenv import load_dotenv

# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq

# pyrefly: ignore [missing-import]
from prompts.sql_prompt import SQL_GENERATOR_SYSTEM_PROMPT

from models.analytical_context import AnalyticalContext
from models.business_knowledge import BusinessKnowledgeResult
from services.observability import ObservabilityCallbackHandler


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class SQLGenerationResult(BaseModel):

    sql: str = Field(
        description="The PostgreSQL SQL query"
    )

    tables_used: list[str] = Field(
        description="Tables used by the SQL query"
    )

    metrics_used: list[str] = Field(
        description="Business metrics used by the SQL query"
    )

    explanation: str = Field(
        description="Short explanation of what the SQL query does"
    )


class SQLGenerator:

    def __init__(self):

        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=GROQ_API_KEY,
            callbacks=[ObservabilityCallbackHandler()],
        )

        self.structured_llm = (
            self.llm.with_structured_output(
                SQLGenerationResult
            )
        )

    def _build_business_knowledge_context(
        self,
        business_knowledge: BusinessKnowledgeResult | None,
    ) -> str:
        if business_knowledge is None or not business_knowledge.matches:
            return "No relevant business knowledge was retrieved."

        sections = []
        for index, match in enumerate(business_knowledge.matches, start=1):
            document = match.document
            sections.append(
                f"MATCH {index}\n"
                f"Document ID: {document.document_id}\n"
                f"Title: {document.title}\n"
                f"Score: {match.score:.4f}\n"
                f"Content: {document.content}\n"
                f"Metadata: {document.metadata}\n"
                f"Matched keywords: {match.matched_keywords}"
            )

        return "\n\n".join(sections)

    def generate(
        self,
        question: str,
        schema: str,
        metadata: str,
        analytical_context: AnalyticalContext | None = None,
        business_knowledge: BusinessKnowledgeResult | None = None,
    ) -> SQLGenerationResult:

        # --------------------------------------------------------
        # Build structured analytical context
        # --------------------------------------------------------

        context_text = (
            "No structured analytical context is available."
        )

        if analytical_context is not None:
            context_text = (
                analytical_context.model_dump_json(
                    indent=2
                )
            )

        business_knowledge_text = (
            self._build_business_knowledge_context(
                business_knowledge
            )
        )

        # --------------------------------------------------------
        # Build SQL generation prompt
        # --------------------------------------------------------

        prompt = f"""
DATABASE SCHEMA:
================

{schema}


SEMANTIC METADATA:
==================

{metadata}


STRUCTURED ANALYTICAL CONTEXT:
===============================

{context_text}


BUSINESS KNOWLEDGE CONTEXT:
============================

{business_knowledge_text}

Use this business knowledge when it defines the meaning or formula of a metric.
Do not invent or alter business definitions. Prefer the retrieved definition over assumptions.


USER QUESTION:
==============

{question}
"""

        messages = [
            (
                "system",
                SQL_GENERATOR_SYSTEM_PROMPT
            ),
            (
                "human",
                prompt
            )
        ]

        result = self.structured_llm.invoke(
            messages
        )

        return result

    def fix_sql(
        self,
        question: str,
        sql: str,
        errors: list[str],
        schema: str,
        metadata: str,
        analytical_context: AnalyticalContext | None = None,
        business_knowledge: BusinessKnowledgeResult | None = None,
    ) -> str:

        # --------------------------------------------------------
        # Build structured analytical context
        # --------------------------------------------------------

        context_text = (
            "No structured analytical context is available."
        )

        if analytical_context is not None:
            context_text = (
                analytical_context.model_dump_json(
                    indent=2
                )
            )

        business_knowledge_text = (
            self._build_business_knowledge_context(
                business_knowledge
            )
        )

        # --------------------------------------------------------
        # Format validation errors
        # --------------------------------------------------------

        error_text = "\n".join(
            f"- {error}"
            for error in errors
        )

        # --------------------------------------------------------
        # Build SQL repair prompt
        # --------------------------------------------------------

        prompt = f"""
You are an expert PostgreSQL SQL developer.

The SQL generated for the user's question is invalid.

Your task is to FIX the SQL.

User Question:
{question}

Database Schema:
{schema}

Semantic Metadata:
{metadata}

Structured Analytical Context:
{context_text}

Business Knowledge Context:
{business_knowledge_text}

Use the retrieved business knowledge when correcting metric definitions or formulas.
Do not replace a retrieved business definition with an assumption.

Previous SQL:
{sql}

Validation Errors:
{error_text}

Rules:
1. Return ONLY the corrected SQL.
2. Do not return markdown.
3. Do not explain your answer.
4. Do not invent tables or columns.
5. Use only tables and columns present in the schema.
6. Preserve the original intent of the user's question.
7. The query must be read-only.
8. Make sure aliases, joins, GROUP BY, ORDER BY,
   CTEs, and column references are valid.
9. Respect the structured analytical context
   when correcting the SQL.
"""

        response = self.llm.invoke(
            prompt
        )

        # pyrefly: ignore [missing-attribute]
        content = response.content.strip()

        # --------------------------------------------------------
        # Remove markdown code fences if returned by the LLM
        # --------------------------------------------------------

        if content.startswith("```"):

            lines = content.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(
                lines
            ).strip()

        return content