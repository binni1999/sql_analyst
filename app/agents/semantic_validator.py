
import sqlglot
from sqlglot import exp


class SemanticValidator:

    def __init__(self, metadata_service):
        self.metadata_service = metadata_service

    # ---------------------------------------------------------
    # Detect metrics requested by the user
    # ---------------------------------------------------------

    def detect_requested_metrics(self, question: str):

        question_lower = question.lower()

        metric_metadata = (
            self.metadata_service
            .get_metric_metadata()
        )

        requested_metrics = []

        # "Sales" is ambiguous in ordinary business language: it can mean
        # units sold or sales value. Treat it as revenue only when the user
        # explicitly asks for revenue/value or uses the established phrase
        # "total sales". In particular, "lowest sales" must not silently
        # impose a revenue formula/alias requirement on a quantity-oriented
        # ranking query.
        import re
        normalized_question = re.sub(r"[^a-z0-9]+", " ", question_lower).strip()
        words = set(normalized_question.split())
        explicit_revenue = bool(words.intersection({"revenue", "revenues"}))
        explicit_sales_value = "sales value" in normalized_question
        explicit_total_sales = "total sales" in normalized_question

        for metric, metadata in metric_metadata.items():
            keywords = metadata.get("keywords", [])
            for keyword in keywords:
                normalized_keyword = re.sub(r"[^a-z0-9]+", " ", keyword.lower()).strip()
                if not normalized_keyword:
                    continue

                # Do not let the broad metadata keyword "sales" match every
                # question containing sales. More specific phrases remain valid.
                if metric == "revenue" and normalized_keyword == "sales":
                    matched = explicit_revenue or explicit_sales_value or explicit_total_sales
                else:
                    matched = normalized_keyword in normalized_question

                if matched:
                    requested_metrics.append(metric)
                    break

        return requested_metrics

    # ---------------------------------------------------------
    # Normalize SQL expressions
    # ---------------------------------------------------------

    def normalize_expression(
        self,
        expression
    ):
        """
        Normalize a SQLGlot expression so that
        table aliases and formatting differences
        do not affect semantic comparison.
        """

        expression = expression.copy()

        for column in expression.find_all(exp.Column):

            # Remove table qualification.
            column.set(
                "table",
                None
            )

        return expression

    # ---------------------------------------------------------
    # Parse metric formula
    # ---------------------------------------------------------

    def parse_formula(
        self,
        formula: str
    ):
        """
        Parse a metric formula into a SQLGlot expression.
        """

        expression = sqlglot.parse_one(
            f"SELECT {formula}",
            read="postgres"
        )

        return expression.expressions[0]

    # ---------------------------------------------------------
    # Formula comparison
    # ---------------------------------------------------------

    def formulas_match(
        self,
        generated_expression,
        expected_formula: str
    ):
        """
        Compare a generated metric expression with its
        metadata formula, allowing ROUND(expression, 2)
        as a presentation wrapper.
        """

        try:

            expected_expression = self.parse_formula(
                expected_formula
            )

            generated_normalized = self.normalize_expression(
                generated_expression
            )

            expected_normalized = self.normalize_expression(
                expected_expression
            )

            # Ignore only a ROUND(..., 2) presentation wrapper.
            if isinstance(generated_normalized, exp.Round):

                precision = generated_normalized.args.get(
                    "decimals"
                )

                if (
                    isinstance(precision, exp.Literal)
                    and not precision.is_string
                    and precision.this == "2"
                ):

                    generated_normalized = (
                        generated_normalized.this
                    )

            return (
                generated_normalized.sql(dialect="postgres")
                == expected_normalized.sql(dialect="postgres")
            )

        except Exception:
            return False

    # ---------------------------------------------------------
    # Find metric aliases in SQL
    # ---------------------------------------------------------

    def find_metric_expressions(
        self,
        sql: str,
        metric: str
    ):

        tree = sqlglot.parse_one(
            sql,
            read="postgres"
        )

        metric_aliases = {
            metric.lower(),
            f"total_{metric.lower()}"
        }

        matches = []

        for alias in tree.find_all(exp.Alias):

            alias_name = alias.alias

            if not alias_name:
                continue

            if alias_name.lower() not in metric_aliases:
                continue

            expression = alias.this

            # Skip only a ROUND presentation wrapper that
            # references an already-computed metric alias.
            #
            # Do not skip formulas such as:
            # SUM(oi.quantity) AS total_quantity
            #
            # These are actual metric definitions, even when
            # their source columns have the same name as the
            # requested metric.
            references_existing_metric = (
                isinstance(expression, exp.Round)
                and any(
                    column.name.lower() in metric_aliases
                    for column in expression.find_all(exp.Column)
                )
            )

            if references_existing_metric:
                continue

            matches.append(expression)

        return matches

    # ---------------------------------------------------------
    # Extract columns used by an expression
    # ---------------------------------------------------------

    def extract_columns(
        self,
        expression
    ):

        columns = set()

        for column in expression.find_all(exp.Column):

            columns.add(
                column.name.lower()
            )

        return columns

    # ---------------------------------------------------------
    # Validate required columns
    # ---------------------------------------------------------

    def validate_required_columns(
        self,
        metric: str,
        expression,
        required_columns
    ):

        errors = []

        used_columns = self.extract_columns(
            expression
        )

        for column in required_columns:

            if column.lower() not in used_columns:

                errors.append(
                    f"Metric '{metric}' requires "
                    f"column '{column}', but the "
                    "metric expression does not use it."
                )

        return errors

    # ---------------------------------------------------------
    # Validate metrics
    # ---------------------------------------------------------

    def validate_metrics(
        self,
        sql: str,
        requested_metrics
    ):

        errors = []

        metric_metadata = (
            self.metadata_service
            .get_metric_metadata()
        )

        for metric in requested_metrics:

            metadata = metric_metadata.get(
                metric
            )

            if not metadata:

                errors.append(
                    f"No metadata definition found "
                    f"for metric '{metric}'."
                )

                continue

            expressions = (
                self.find_metric_expressions(
                    sql,
                    metric
                )
            )

            if not expressions:

                errors.append(
                    f"Metric '{metric}' is requested "
                    "but the SQL does not expose "
                    f"'{metric}' as a metric alias."
                )

                continue

            required_columns = metadata.get(
                "required_columns",
                []
            )

            for expression in expressions:

                errors.extend(
                    self.validate_required_columns(
                        metric=metric,
                        expression=expression,
                        required_columns=required_columns
                    )
                )

                expected_formula = metadata.get(
                    "formula"
                )

                formula_type = metadata.get(
                    "formula_type"
                )

                if (
                    expected_formula
                    and formula_type == "sql_expression"
                ):

                    if not self.formulas_match(
                        generated_expression=expression,
                        expected_formula=expected_formula
                    ):

                        errors.append(
                            f"Metric '{metric}' does not "
                            "match the expected formula."
                        )

        return errors

    # ---------------------------------------------------------
    # Validate metrics reported by the LLM
    # ---------------------------------------------------------

    def validate_reported_metrics(
        self,
        metrics_used
    ):

        errors = []

        metric_metadata = (
            self.metadata_service
            .get_metric_metadata()
        )

        for metric in metrics_used:

            if metric not in metric_metadata:

                errors.append(
                    f"Unknown metric reported: "
                    f"{metric}"
                )

        return errors

    # ---------------------------------------------------------
    # Main validation method
    # ---------------------------------------------------------

    def validate(
        self,
        question: str,
        sql: str,
        metrics_used: list[str]
    ):

        errors = []

        # Parse SQL first.
        try:

            sqlglot.parse_one(
                sql,
                read="postgres"
            )

        except Exception as e:

            return {
                "is_valid": False,
                "errors": [
                    f"Unable to parse SQL "
                    f"for semantic validation: {str(e)}"
                ]
            }

        # Validate metrics reported by the LLM.
        errors.extend(
            self.validate_reported_metrics(
                metrics_used
            )
        )

        # Detect metrics from the user's question.
        requested_metrics = (
            self.detect_requested_metrics(
                question
            )
        )

        # Validate requested metrics.
        errors.extend(
            self.validate_metrics(
                sql=sql,
                requested_metrics=requested_metrics
            )
        )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
