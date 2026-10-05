from agents.sql_generator import SQLGenerator

from agents.sql_validator import SQLValidator

from database.service import DatabaseService

from agents.semantic_validator import SemanticValidator

import inspect

from models.agent import SQLResult

from models.state import AgentState

from models.analytical_context import AnalyticalContext

from models.business_knowledge import BusinessKnowledgeResult

from models.execution_trace import ExecutionTraceEvent



from validation.context_validator import ContextValidator

from validation.sql_requirements import SQLRequirementsBuilder

from validation.sql_error_classifier import SQLErrorClassifier

from validation.sql_repair_strategy import SQLRepairStrategy

from tools.sql_tool import ToolCallingExecutor





class SQLAgent:



    def __init__(

        self,

        sql_generator: SQLGenerator,

        sql_validator: SQLValidator,

        semantic_validator: SemanticValidator,

        db: DatabaseService,

        context_validator: ContextValidator | None = None,

        requirements_builder: SQLRequirementsBuilder | None = None,

        error_classifier: SQLErrorClassifier | None = None,

        repair_strategy: SQLRepairStrategy | None = None,

        max_retries: int = 3,

        tool_executor: ToolCallingExecutor | None = None,

        tool_model=None,

    ):

        self.sql_generator = sql_generator

        self.sql_validator = sql_validator

        self.db = db

        self.semantic_validator = semantic_validator



        self.context_validator = (

            context_validator

            if context_validator is not None

            else ContextValidator()

        )



        self.requirements_builder = (

            requirements_builder

            if requirements_builder is not None

            else SQLRequirementsBuilder()

        )



        self.error_classifier = (

            error_classifier

            if error_classifier is not None

            else SQLErrorClassifier()

        )



        self.repair_strategy = (

            repair_strategy

            if repair_strategy is not None

            else SQLRepairStrategy()

        )



        self.max_retries = max_retries



        # Step 59: optional tool-calling capability. The existing

        # deterministic SQL pipeline remains the source of truth;

        # tool calling supplies runtime discovery/validation capabilities.

        self.tool_executor = tool_executor

        self.tool_model = tool_model





    def _fix_sql(

        self,

        *,

        question: str,

        sql: str,

        errors: list[str],

        schema: str,

        metadata: str,

        analytical_context: AnalyticalContext | None,

        business_knowledge: BusinessKnowledgeResult | None,

    ) -> str:

        """

        Call SQLGenerator.fix_sql() while remaining backward compatible

        with older SQLGenerator implementations/test doubles that do not

        accept business_knowledge.

        """



        fix_method = self.sql_generator.fix_sql



        parameters = inspect.signature(fix_method).parameters



        kwargs = {

            "question": question,

            "sql": sql,

            "errors": errors,

            "schema": schema,

            "metadata": metadata,

            "analytical_context": analytical_context,

        }



        if "business_knowledge" in parameters:

            kwargs["business_knowledge"] = business_knowledge



        return fix_method(**kwargs)



    # ============================================================

    # TOOL-CALLING CAPABILITY

    # ============================================================



    def _run_tool_discovery(

        self,

        *,

        question: str,

        analytical_context: AnalyticalContext | None,

        business_knowledge: BusinessKnowledgeResult | None,

        execution_trace: list[dict[str, object]],

    ) -> None:

        """Let the SQL-agent model select discovery tools before SQL generation.



        Step 59 deliberately limits autonomous discovery to schema/metadata.

        Deterministic validation, repair, and the downstream execution path

        remain unchanged so existing safety and semantic guarantees are kept.

        """

        if self.tool_executor is None or self.tool_model is None:

            return



        allowed_names = {"get_schema", "get_metadata"}

        discovery_tools = [

            tool for tool in self.tool_executor.tools

            if tool.name in allowed_names

        ]



        if not discovery_tools:

            return



        discovery_executor = ToolCallingExecutor(

            discovery_tools,

            max_retries=self.tool_executor.max_retries,

            max_tool_rounds=min(self.tool_executor.max_tool_rounds, 2),

        )



        context_text = (

            analytical_context.model_dump_json()

            if analytical_context is not None

            else "No structured analytical context is available."

        )

        business_knowledge_text = (

            "No business knowledge was retrieved."

        )



        if business_knowledge is not None:

            business_knowledge_text = "\n\n".join(

                (

                    f"Document: {match.document.title}\n"

                    f"Source: {match.document.source}\n"

                    f"Content: {match.document.content}\n"

                    f"Score: {match.score}"

                )

                for match in business_knowledge.matches

            )



        messages = [

            (

                "system",

                "You are the SQL agent's database discovery planner. "

                "Use tools only when needed to retrieve schema or business metadata. "

                "Do not execute SQL, validate SQL, or repair SQL in this discovery phase. "

                "After receiving tool results, return a brief planning response.",

            ),

            (

                "human",

                f"User question:\n{question}\n\n"

                f"Structured analytical context:\n{context_text}\n\n"

                "Business knowledge retrieved:\n"

                f"{business_knowledge_text}\n\n"

                "Select get_schema and/or get_metadata when their information is useful.",

            ),

        ]



        try:

            discovery_executor.run(

                self.tool_model,

                messages,

                execution_trace=execution_trace,

            )

        except Exception as exc:

            # Discovery is an optional Step 59 capability. A discovery

            # model/tool failure must not make the deterministic SQL

            # generation + validation pipeline fail. Continue with the

            # existing schema/metadata already supplied by MetadataAgent.

            self._add_trace_event(

                execution_trace,

                stage="tool_call",

                attempt=0,

                status="failed",

                message=(

                    "SQL discovery tool calling failed; "

                    f"falling back to deterministic metadata/schema: {exc}"

                ),

                error_type="tool",

                metadata={

                    "phase": "discovery",

                    "fallback": "deterministic_metadata_schema",

                },

            )



    # ============================================================

    # ERROR FORMATTING

    # ============================================================



    def _build_repair_errors(

        self,

        *,

        syntax_errors: list[str] | None = None,

        database_errors: list[str] | None = None,

        semantic_errors: list[str] | None = None,

        context_errors: list[str] | None = None,

        analytical_context: AnalyticalContext | None = None,

        requirements=None,

    ) -> list[str]:

        """

        Classify validator errors and convert them into

        targeted repair instructions.



        AnalyticalContext and SQLRequirements are passed to the

        repair strategy so that the generated repair instructions

        preserve the user's analytical intent.

        """



        classified_errors = self.error_classifier.classify(

            syntax_errors=syntax_errors or [],

            database_errors=database_errors or [],

            semantic_errors=semantic_errors or [],

            context_errors=context_errors or [],

        )



        return self.repair_strategy.build_instructions(

            classified_errors,

            analytical_context=analytical_context,

            requirements=requirements,

        )



    def _handle_repair_failure(

        self,

        *,

        sql: str,

        attempt: int,

        errors: list[str],

        exc: Exception,

        execution_trace: list[dict[str, object]],

    ):

        """

        Convert an unrecoverable SQL repair exception into a

        structured failure result while preserving the SQL,

        validation attempt, previous validation errors,

        repair exception, and execution trace.

        """



        repair_error = (

            f"SQL repair failed on attempt {attempt}: {str(exc)}"

        )



        self._add_trace_event(

            execution_trace,

            stage="repair",

            attempt=attempt,

            status="failed",

            message=repair_error,

            error_type="repair",

            metadata={

                "repair_strategy": self.repair_strategy.__class__.__name__,

                "exception_type": exc.__class__.__name__,

            },

        )



        print("\nSQL repair failed.")

        print(f"Error: {repair_error}")



        return {

            "success": False,

            "sql": sql,

            "attempts": attempt,

            "errors": [

                *errors,

                repair_error,

            ],

            "execution_trace": execution_trace,

        }



    def _add_trace_event(

        self,

        trace: list[dict[str, object]],

        *,

        stage: str,

        attempt: int,

        status: str,

        message: str | None = None,

        error_type: str | None = None,

        metadata: dict[str, object] | None = None,

    ):

        event = ExecutionTraceEvent(

            stage=stage,

            attempt=attempt,

            status=status,

            message=message,

            error_type=error_type,

            metadata=metadata or {},

        )



        trace.append(

            event.model_dump(exclude_none=True)

        )



    def _repair_sql(

        self,

        *,

        question: str,

        sql: str,

        errors: list[str],

        schema: str,

        metadata: str,

        analytical_context: AnalyticalContext | None,

        business_knowledge: BusinessKnowledgeResult | None,

        execution_trace: list[dict[str, object]],

    ) -> str:

        """Repair SQL through the configured tool layer when available."""

        if (

            self.tool_executor is not None

            and "repair_sql" in {tool.name for tool in self.tool_executor.tools}

        ):

            try:

                result = self.tool_executor.execute(

                    "repair_sql",

                    {

                        "question": question,

                        "sql": sql,

                        "errors": errors,

                        "analytical_context": (

                            analytical_context.model_dump()

                            if analytical_context is not None

                            else None

                        ),

                        "business_knowledge": (

                            business_knowledge.model_dump()

                            if business_knowledge is not None

                            else None

                        ),

                    },

                    execution_trace=execution_trace,

                )

                return str(result)

            except Exception as exc:

                self._add_trace_event(

                    execution_trace,

                    stage="tool_call",

                    attempt=0,

                    status="failed",

                    message=f"repair_sql tool failed; falling back to SQLGenerator: {exc}",

                    error_type="tool",

                    metadata={"tool": "repair_sql", "fallback": "sql_generator"},

                )



        return self._fix_sql(

            question=question,

            sql=sql,

            errors=errors,

            schema=schema,

            metadata=metadata,

            analytical_context=analytical_context,

            business_knowledge=business_knowledge,

        )



    # ============================================================

    # GENERATE + VALIDATE + REPAIR SQL

    # ============================================================



    def _generate_sql(

        self,

        *,

        question: str,

        schema: str,

        metadata: str,

        analytical_context: AnalyticalContext | None,

        business_knowledge: BusinessKnowledgeResult | None,

    ):

        """

        Generate SQL while remaining backward compatible with older

        SQLGenerator implementations/test doubles that do not yet accept

        business_knowledge.

        """



        generate_method = self.sql_generator.generate



        parameters = inspect.signature(generate_method).parameters



        kwargs = {

            "question": question,

            "schema": schema,

            "metadata": metadata,

            "analytical_context": analytical_context,

        }



        if "business_knowledge" in parameters:

            kwargs["business_knowledge"] = business_knowledge



        return generate_method(**kwargs)







    def _generate_valid_sql(
        self,
        *,
        question: str,
        schema: str,
        schemas: list[dict],
        metadata: str,
        analytical_context: AnalyticalContext | None,
        business_knowledge: BusinessKnowledgeResult | None,
    ):
        """
        Call generate_valid_sql() while remaining backward compatible
        with older SQLAgent subclasses/test doubles that do not yet
        accept analytical_context or business_knowledge.
        """

        generate_method = self.generate_valid_sql
        parameters = inspect.signature(generate_method).parameters

        kwargs = {
            "question": question,
            "schema": schema,
            "schemas": schemas,
            "metadata": metadata,
        }

        if "analytical_context" in parameters:
            kwargs["analytical_context"] = analytical_context

        if "business_knowledge" in parameters:
            kwargs["business_knowledge"] = business_knowledge

        return generate_method(**kwargs)


    def generate_valid_sql(

        self,

        question: str,

        schema: str,

        schemas: list[dict],

        metadata: str,

        analytical_context: AnalyticalContext | None = None,

        business_knowledge: BusinessKnowledgeResult | None = None,

    ):

        """

        Generate SQL and continuously validate/repair it.



        Validation pipeline:



            Generate SQL

                 ↓

            SQLGlot validation

                 ↓

            PostgreSQL validation

                 ↓

            Semantic validation

                 ↓

            Context validation

                 ↓

            Success



        If validation fails:



            Validation Error

                 ↓

            Classify Error

                 ↓

            Context-aware Repair Strategy

                 ↓

            LLM SQL Repair

                 ↓

            Validate Again

        """



        # --------------------------------------------------------

        # STEP 1: Initialize execution trace

        # --------------------------------------------------------



        execution_trace: list[dict[str, object]] = []



        # --------------------------------------------------------

        # STEP 2: Tool-assisted discovery

        # --------------------------------------------------------



        self._run_tool_discovery(

            question=question,

            analytical_context=analytical_context,

            business_knowledge=business_knowledge,

            execution_trace=execution_trace,

        )



        # --------------------------------------------------------

        # STEP 3: Generate initial SQL

        # --------------------------------------------------------



        generated = self._generate_sql(

            question=question,

            schema=schema,

            metadata=metadata,

            analytical_context=analytical_context,

            business_knowledge=business_knowledge,

        )



        sql = generated.sql

        metrics_used = generated.metrics_used



        self._add_trace_event(

            execution_trace,

            stage="generation",

            attempt=0,

            status="success",

            message="SQL generated successfully.",

            metadata={

                "component": self.sql_generator.__class__.__name__,

            },

        )



        # --------------------------------------------------------

        # Convert AnalyticalContext into deterministic

        # SQL requirements used by ContextValidator.

        # --------------------------------------------------------



        requirements = self.requirements_builder.build(

            analytical_context

        )



        print("\nINITIAL GENERATED SQL")

        print("=" * 60)

        print(sql)



        errors = []



        # --------------------------------------------------------

        # STEP 3: Retry loop

        # --------------------------------------------------------



        for attempt in range(1, self.max_retries + 1):



            print(

                f"\nSQL VALIDATION ATTEMPT "

                f"{attempt}/{self.max_retries}"

            )



            # ====================================================

            # STEP 4: SQLGlot validation

            # ====================================================



            tool_validation = None

            has_validate_tool = (

                self.tool_executor is not None

                and "validate_sql" in {tool.name for tool in self.tool_executor.tools}

            )



            if has_validate_tool:

                try:

                    tool_validation = self.tool_executor.execute(

                        "validate_sql",

                        {"sql": sql},

                        execution_trace=execution_trace,

                    )

                except Exception as exc:

                    self._add_trace_event(

                        execution_trace,

                        stage="tool_call",

                        attempt=attempt,

                        status="failed",

                        message=f"validate_sql tool failed; falling back to deterministic validators: {exc}",

                        error_type="tool",

                        metadata={"tool": "validate_sql", "fallback": "deterministic_validation"},

                    )

                    tool_validation = None



            if tool_validation is not None:

                syntax_valid = bool(tool_validation.get("syntax_valid"))

                validation_errors = list(tool_validation.get("errors", []))



                class ToolValidationResult:

                    is_valid = syntax_valid

                    errors = validation_errors



                validation = ToolValidationResult()

            else:

                validation = self.sql_validator.validate(

                    sql,

                    schemas,

                )



            if not validation.is_valid:



                self._add_trace_event(

                    execution_trace,

                    stage="sqlglot_validation",

                    attempt=attempt,

                    status="failed",

                    message="SQLGlot validation failed.",

                    error_type="syntax",

                    metadata={

                        "validator": self.sql_validator.__class__.__name__,

                        "error_count": len(validation.errors),

                    },

                )



                print("\nSQLGlot validation failed.")

                print("Errors:")



                for error in validation.errors:

                    print(f"- {error}")



                syntax_errors = validation.errors



                errors.extend(syntax_errors)



                # Build targeted repair instructions.

                repair_errors = self._build_repair_errors(

                    syntax_errors=syntax_errors,

                    analytical_context=analytical_context,

                    requirements=requirements,

                )



                # ------------------------------------------------

                # Retry if attempts remain

                # ------------------------------------------------



                if attempt < self.max_retries:



                    print(

                        "\nSending classified SQLGlot errors "

                        "back to LLM..."

                    )



                    try:

                        sql = self._repair_sql(

                            question=question,

                            sql=sql,

                            errors=repair_errors,

                            schema=schema,

                            metadata=metadata,

                            analytical_context=analytical_context,

                            business_knowledge=business_knowledge,

                            execution_trace=execution_trace,

                        )



                    except Exception as exc:

                        return self._handle_repair_failure(

                            sql=sql,

                            attempt=attempt,

                            errors=errors,

                            exc=exc,

                            execution_trace=execution_trace,

                        )



                    self._add_trace_event(

                        execution_trace,

                        stage="repair",

                        attempt=attempt,

                        status="success",

                        message="SQL repaired successfully.",

                        metadata={

                            "repair_strategy": self.repair_strategy.__class__.__name__,

                        },

                    )



                    print("\nCORRECTED SQL")

                    print("=" * 60)

                    print(sql)



                    continue



                # ------------------------------------------------

                # Retry limit reached

                # ------------------------------------------------



                print(

                    "\nMaximum SQL retry limit reached."

                )



                return {

                    "success": False,

                    "sql": sql,

                    "attempts": attempt,

                    "errors": errors,

                    "execution_trace": execution_trace,

                }



            print("SQLGlot validation successful.")



            self._add_trace_event(

                execution_trace,

                stage="sqlglot_validation",

                attempt=attempt,

                status="success",

                message="SQLGlot validation successful.",

                metadata={

                    "validator": self.sql_validator.__class__.__name__,

                },

            )



            # ====================================================

            # STEP 5: PostgreSQL validation

            # ====================================================



            print(

                "\nRunning PostgreSQL validation..."

            )



            if tool_validation is not None:

                database_validation = {

                    "valid": bool(tool_validation.get("database_valid")),

                    "error": next(

                        (

                            error

                            for error in tool_validation.get("errors", [])

                            if error

                            and error not in validation_errors

                        ),

                        None,

                    ),

                }

            else:

                if self.db is None:

                    database_validation = {

                        "valid": True,

                        "error": None,

                    }

                else:

                    database_validation = self.db.validate_with_database(sql)



            if not database_validation["valid"]:



                database_error = database_validation.get(

                    "error",

                    "Unknown PostgreSQL validation error.",

                )



                self._add_trace_event(

                    execution_trace,

                    stage="database_validation",

                    attempt=attempt,

                    status="failed",

                    message=str(database_error),

                    error_type="database",

                    metadata={

                        "validator": self.db.__class__.__name__,

                    },

                )



                print(

                    "\nPostgreSQL validation failed."

                )



                print(

                    f"Error: {database_error}"

                )



                database_errors = [database_error]



                errors.extend(database_errors)



                # Build targeted repair instructions.

                repair_errors = self._build_repair_errors(

                    database_errors=database_errors,

                    analytical_context=analytical_context,

                    requirements=requirements,

                )



                # ------------------------------------------------

                # Retry if attempts remain

                # ------------------------------------------------



                if attempt < self.max_retries:



                    print(

                        "\nSending classified PostgreSQL error "

                        "back to LLM..."

                    )



                    try:

                        sql = self._repair_sql(

                            question=question,

                            sql=sql,

                            errors=repair_errors,

                            schema=schema,

                            metadata=metadata,

                            analytical_context=analytical_context,

                            business_knowledge=business_knowledge,

                            execution_trace=execution_trace,

                        )



                    except Exception as exc:

                        return self._handle_repair_failure(

                            sql=sql,

                            attempt=attempt,

                            errors=errors,

                            exc=exc,

                            execution_trace=execution_trace,

                        )



                    self._add_trace_event(

                        execution_trace,

                        stage="repair",

                        attempt=attempt,

                        status="success",

                        message="SQL repaired successfully.",

                        metadata={

                            "repair_strategy": self.repair_strategy.__class__.__name__,

                        },

                    )



                    print("\nCORRECTED SQL")

                    print("=" * 60)

                    print(sql)



                    continue



                print(

                    "\nMaximum SQL retry limit reached."

                )



                return {

                    "success": False,

                    "sql": sql,

                    "attempts": attempt,

                    "errors": errors,

                    "execution_trace": execution_trace,

                }



            print(

                "PostgreSQL validation successful."

            )



            self._add_trace_event(

                execution_trace,

                stage="database_validation",

                attempt=attempt,

                status="success",

                message="PostgreSQL validation successful.",

                metadata={

                    "validator": self.db.__class__.__name__,

                },

            )



            # ====================================================

            # STEP 6: Semantic validation

            # ====================================================



            semantic_validation = (

                self.semantic_validator.validate(

                    question=question,

                    sql=sql,

                    metrics_used=metrics_used,

                )

            )



            if not semantic_validation["is_valid"]:



                self._add_trace_event(

                    execution_trace,

                    stage="semantic_validation",

                    attempt=attempt,

                    status="failed",

                    message="Semantic validation failed.",

                    error_type="semantic",

                    metadata={

                        "validator": self.semantic_validator.__class__.__name__,

                        "error_count": len(

                            semantic_validation["errors"]

                        ),

                    },

                )



                print(

                    "\nSemantic validation failed."

                )



                print("Errors:")



                for error in semantic_validation["errors"]:

                    print(f"- {error}")



                semantic_errors = (

                    semantic_validation["errors"]

                )



                errors.extend(semantic_errors)



                # Build targeted repair instructions.

                repair_errors = self._build_repair_errors(

                    semantic_errors=semantic_errors,

                    analytical_context=analytical_context,

                    requirements=requirements,

                )



                # ------------------------------------------------

                # Retry if attempts remain

                # ------------------------------------------------



                if attempt < self.max_retries:



                    print(

                        "\nSending classified semantic errors "

                        "back to LLM..."

                    )



                    try:

                        sql = self._repair_sql(

                            question=question,

                            sql=sql,

                            errors=repair_errors,

                            schema=schema,

                            metadata=metadata,

                            analytical_context=analytical_context,

                            business_knowledge=business_knowledge,

                            execution_trace=execution_trace,

                        )



                    except Exception as exc:

                        return self._handle_repair_failure(

                            sql=sql,

                            attempt=attempt,

                            errors=errors,

                            exc=exc,

                            execution_trace=execution_trace,

                        )



                    self._add_trace_event(

                        execution_trace,

                        stage="repair",

                        attempt=attempt,

                        status="success",

                        message="SQL repaired successfully.",

                        metadata={

                            "repair_strategy": self.repair_strategy.__class__.__name__,

                        },

                    )



                    print("\nCORRECTED SQL")

                    print("=" * 60)

                    print(sql)



                    continue



                print(

                    "\nMaximum SQL retry limit reached."

                )



                return {

                    "success": False,

                    "sql": sql,

                    "attempts": attempt,

                    "errors": errors,

                    "execution_trace": execution_trace,

                }



            print(

                "Semantic validation successful."

            )



            self._add_trace_event(

                execution_trace,

                stage="semantic_validation",

                attempt=attempt,

                status="success",

                message="Semantic validation successful.",

                metadata={

                    "validator": self.semantic_validator.__class__.__name__,

                },

            )



            # ====================================================

            # STEP 7: Context validation

            # ====================================================



            context_validation = (

                self.context_validator.validate(

                    sql=sql,

                    requirements=requirements,

                    schemas=schemas,

                )

            )



            if not context_validation.is_valid:



                self._add_trace_event(

                    execution_trace,

                    stage="context_validation",

                    attempt=attempt,

                    status="failed",

                    message="Context validation failed.",

                    error_type="context",

                    metadata={

                        "validator": self.context_validator.__class__.__name__,

                        "error_count": len(

                            context_validation.errors

                        ),

                    },

                )



                print(

                    "\nContext validation failed."

                )



                print("Errors:")



                for error in context_validation.errors:

                    print(f"- {error}")



                context_errors = (

                    context_validation.errors

                )



                errors.extend(context_errors)



                # Build targeted repair instructions using

                # both AnalyticalContext and SQLRequirements.

                repair_errors = self._build_repair_errors(

                    context_errors=context_errors,

                    analytical_context=analytical_context,

                    requirements=requirements,

                )



                # ------------------------------------------------

                # Retry if attempts remain

                # ------------------------------------------------



                if attempt < self.max_retries:



                    print(

                        "\nSending classified context validation "

                        "errors back to LLM..."

                    )



                    try:

                        sql = self._repair_sql(

                            question=question,

                            sql=sql,

                            errors=repair_errors,

                            schema=schema,

                            metadata=metadata,

                            analytical_context=analytical_context,

                            business_knowledge=business_knowledge,

                            execution_trace=execution_trace,

                        )



                    except Exception as exc:

                        return self._handle_repair_failure(

                            sql=sql,

                            attempt=attempt,

                            errors=errors,

                            exc=exc,

                            execution_trace=execution_trace,

                        )



                    self._add_trace_event(

                        execution_trace,

                        stage="repair",

                        attempt=attempt,

                        status="success",

                        message="SQL repaired successfully.",

                        metadata={

                            "repair_strategy": self.repair_strategy.__class__.__name__,

                        },

                    )



                    print("\nCORRECTED SQL")

                    print("=" * 60)

                    print(sql)



                    continue



                print(

                    "\nMaximum SQL retry limit reached."

                )



                return {

                    "success": False,

                    "sql": sql,

                    "attempts": attempt,

                    "errors": errors,

                    "execution_trace": execution_trace,

                }



            print(

                "Context validation successful."

            )



            self._add_trace_event(

                execution_trace,

                stage="context_validation",

                attempt=attempt,

                status="success",

                message="Context validation successful.",

                metadata={

                    "validator": self.context_validator.__class__.__name__,

                },

            )



            # ====================================================

            # STEP 8: Everything passed

            # ====================================================



            return {

                "success": True,

                "sql": sql,

                "attempts": attempt,

                "errors": [],

                "execution_trace": execution_trace,

            }



        # --------------------------------------------------------

        # Safety fallback

        # --------------------------------------------------------



        return {

            "success": False,

            "sql": sql,

            "attempts": self.max_retries,

            "errors": errors,

            "execution_trace": execution_trace,

        }



    # ============================================================

    # AGENT ENTRY POINT

    # ============================================================



    def run(self, state: AgentState):



        # --------------------------------------------------------

        # STEP 1: Metadata is required

        # --------------------------------------------------------



        if state.metadata is None:



            error = (

                "Metadata is required before SQL generation."

            )



            state.sql = SQLResult(

                success=False,

                sql=None,

                attempts=0,

                errors=[error],

            )



            state.mark_failure(error)



            return state



        # --------------------------------------------------------

        # STEP 2: Extract metadata

        # --------------------------------------------------------



        question = state.question



        schema = state.metadata.schema_text



        schemas = state.metadata.schemas



        metadata = state.metadata.metadata



        analytical_context = state.analytical_context

        business_knowledge = state.business_knowledge



        # --------------------------------------------------------

        # STEP 3: Generate + validate + repair SQL

        # --------------------------------------------------------



        try:



            if analytical_context is None:



                result = self._generate_valid_sql(
                    question=question,
                    schema=schema,
                    schemas=schemas,
                    metadata=metadata,
                    analytical_context=None,
                    business_knowledge=business_knowledge,
                )



            else:



                result = self._generate_valid_sql(
                    question=question,
                    schema=schema,
                    schemas=schemas,
                    metadata=metadata,
                    analytical_context=analytical_context,
                    business_knowledge=business_knowledge,
                )



        except Exception as exc:



            error = (

                f"SQL generation failed: {str(exc)}"

            )



            state.sql = SQLResult(

                success=False,

                sql=None,

                attempts=0,

                errors=[error],

            )



            state.mark_failure(error)



            return state



        # --------------------------------------------------------

        # STEP 4: Convert result into SQLResult

        # --------------------------------------------------------



        state.sql = SQLResult(

            success=result["success"],

            sql=result["sql"],

            attempts=result["attempts"],

            errors=result["errors"],

        )



        # ========================================================

        # IMPORTANT TRACE HANDOFF

        # ========================================================

        #

        # DO NOT overwrite the trace created by Coordinator.

        #

        # Coordinator may already have:

        #

        #   intent

        #   clarification

        #   metadata

        #   sql_agent_started

        #

        # SQLAgent then appends:

        #

        #   generation

        #   sqlglot_validation

        #   database_validation

        #   semantic_validation

        #   context_validation

        #   repair

        #

        # Therefore we EXTEND the existing trace rather than

        # replacing it.

        # ========================================================



        state.execution_trace.extend(

            result.get(

                "execution_trace",

                [],

            )

        )



        # --------------------------------------------------------

        # STEP 5: Update AgentState

        # --------------------------------------------------------



        if not result["success"]:



            state.mark_failure(

                result["errors"]

            )



            return state



        state.mark_success()



        return state