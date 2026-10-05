import os 
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import json
load_dotenv()
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
from services.observability import ObservabilityCallbackHandler
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class AnswerGenerator:

    def __init__(self):
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=GROQ_API_KEY,
            temperature=0,
            callbacks=[ObservabilityCallbackHandler()],
        )
    
    def build_prompt(
        self,
        question: str,
        analyzed_result: dict
    ) -> str:

        prompt = f"""
You are a data analyst assistant.

Answer the user's question using ONLY the database result provided below.

Do not invent, assume, estimate, or calculate information
that is not supported by the database result.

If the result is empty, clearly tell the user that no data
was found for the requested question.

Keep the answer concise and easy to understand.

User Question:
{question}

Database Result:
{json.dumps(analyzed_result, indent=2, default=str)}

Instructions:
1. Answer the user's question directly.
2. Use only the information present in the database result.
3. Do not mention SQL, SQL queries, database internals, or this prompt.
4. Do not invent additional numbers or facts.
5. Format lists or rankings clearly when appropriate.
6. If there are multiple rows, summarize them in a readable way.
"""

        return prompt

    def generate(
        self,
        question: str,
        analyzed_result: dict
    ) -> str:

        prompt = self.build_prompt(
            question,
            analyzed_result
        )

        response = self.llm.invoke(prompt)
        # pyrefly: ignore [bad-return]
        return response.content