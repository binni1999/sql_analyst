from agents.business_knowledge_agent import BusinessKnowledgeAgent
from knowledge.business_documents import BUSINESS_KNOWLEDGE_DOCUMENTS
from services.business_knowledge_retriever import BusinessKnowledgeRetriever
from agents.clarification_resolver import ClarificationResolver
from services.conversation_service import ConversationService
from agents.sql_generator import SQLGenerator
from agents.sql_validator import SQLValidator
from agents.sql_agent import SQLAgent
from agents.sql_executor import SQLExecutor
from agents.result_analyzer import ResultAnalyzer
from agents.answer_generator import AnswerGenerator

from graph.workflow import DataAnalystGraph
from agents.metadata_agent import MetadataAgent
from agents.analytics_agent import AnalyticsAgent

from database.service import DatabaseService
from database.metadata_service import MetadataService

from services.question_validator import QuestionValidator
from services.data_analyst_service import DataAnalystService

from agents.semantic_validator import SemanticValidator
from agents.intent_agent import IntentAgent
from agents.clarification_agent import ClarificationAgent
from agents.follow_up_resolver import FollowUpResolver
from agents.analytical_context_extractor import (
    AnalyticalContextExtractor
)
from tools.sql_tool import ToolCallingExecutor, build_sql_tools
from services.checkpoint_store import PostgresCheckpointStore
from services.memory_service import ConversationMemoryService
from security.guardrails import SQLSecurityGuardrail
from security.executor import SecureSQLExecutor
from security.policies import SQLSecurityPolicy
from security.input_guardrails import PromptInjectionGuardrail, PromptSecurityPolicy

def create_data_analyst_service() -> DataAnalystService:

    # -----------------------------------------
    # Database
    # -----------------------------------------

    db = DatabaseService()
    intent_agent = IntentAgent()
    clarification_agent = ClarificationAgent()

    metadata_service = MetadataService()
    follow_up_resolver = FollowUpResolver()
    analytical_context_extractor = (
        AnalyticalContextExtractor()
    )

    # -----------------------------------------
    # Metadata Agent
    # -----------------------------------------

    metadata_agent = MetadataAgent(
        metadata_service=metadata_service,
        db=db
    )

    # -----------------------------------------
    # SQL components
    # -----------------------------------------

    sql_generator = SQLGenerator()

    sql_validator = SQLValidator()

    semantic_validator = SemanticValidator(
        metadata_service=metadata_service
    )

    # Step 58/59 tool-calling foundation + Step 67 security boundary.
    security_policy = SQLSecurityPolicy()
    security_guardrail = SQLSecurityGuardrail(security_policy)
    secure_executor = SecureSQLExecutor(
        db=db,
        guardrail=security_guardrail,
    )

    tool_executor = ToolCallingExecutor(
        build_sql_tools(
            db=db,
            metadata_service=metadata_service,
            sql_validator=sql_validator,
            sql_generator=sql_generator,
            secure_executor=secure_executor,
        )
    )

    sql_agent = SQLAgent(
        sql_generator=sql_generator,
        sql_validator=sql_validator,
        semantic_validator=semantic_validator,
        db=db,
        tool_executor=tool_executor,
        tool_model=sql_generator.llm,
    )

    # -----------------------------------------
    # Execution
    # -----------------------------------------

    sql_executor = SQLExecutor(db, secure_executor=secure_executor)

    # -----------------------------------------
    # Result analysis
    # -----------------------------------------

    result_analyzer = ResultAnalyzer()

    # -----------------------------------------
    # Analytics Agent
    # -----------------------------------------

    analytics_agent = AnalyticsAgent(
        sql_executor=sql_executor,
        result_analyzer=result_analyzer
    )

    # -----------------------------------------
    # Answer generation
    # -----------------------------------------

    answer_generator = AnswerGenerator()

    # -----------------------------------------
    # LangGraph orchestration
    # -----------------------------------------

    checkpoint_store = PostgresCheckpointStore()

    business_knowledge_retriever = BusinessKnowledgeRetriever(
        BUSINESS_KNOWLEDGE_DOCUMENTS
    )

    business_knowledge_agent = BusinessKnowledgeAgent(
        retriever=business_knowledge_retriever,
        top_k=3,
    )

    graph = DataAnalystGraph(
        intent_agent=intent_agent,
        clarification_agent=clarification_agent,
        metadata_agent=metadata_agent,
        sql_agent=sql_agent,
        analytics_agent=analytics_agent,
        answer_generator=answer_generator,
        business_knowledge_agent=business_knowledge_agent,
        checkpointer=checkpoint_store.checkpointer,
    )

    # -----------------------------------------
    # Application Service
    # -----------------------------------------

    question_validator = QuestionValidator()
    prompt_guardrail = PromptInjectionGuardrail(PromptSecurityPolicy())

    conversation_service = ConversationService()

    clarification_resolver = ClarificationResolver()

    memory_service = ConversationMemoryService()

    service = DataAnalystService(
        graph=graph,
        question_validator=question_validator,
        conversation_service=conversation_service,
        clarification_resolver=clarification_resolver,
        follow_up_resolver=follow_up_resolver,
        analytical_context_extractor=(
            analytical_context_extractor
        ),
        tool_executor=tool_executor,
        memory_service=memory_service,
        prompt_guardrail=prompt_guardrail,
    )

    return service
