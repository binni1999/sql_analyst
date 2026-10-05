from models.sql_error import SQLErrorType
from validation.sql_error_classifier import SQLErrorClassifier


def test_classify_syntax_errors():
    classifier = SQLErrorClassifier()

    errors = classifier.classify_syntax(
        ["Invalid SQL syntax."]
    )

    assert len(errors) == 1
    assert errors[0].error_type == SQLErrorType.SYNTAX
    assert errors[0].message == "Invalid SQL syntax."
    assert errors[0].source == "SQLValidator"


def test_classify_database_errors():
    classifier = SQLErrorClassifier()

    errors = classifier.classify_database(
        ["column does not exist"]
    )

    assert len(errors) == 1
    assert errors[0].error_type == SQLErrorType.DATABASE
    assert errors[0].message == "column does not exist"
    assert errors[0].source == "DatabaseValidator"


def test_classify_semantic_errors():
    classifier = SQLErrorClassifier()

    errors = classifier.classify_semantic(
        ["Revenue formula is incorrect."]
    )

    assert len(errors) == 1
    assert errors[0].error_type == SQLErrorType.SEMANTIC
    assert errors[0].message == "Revenue formula is incorrect."
    assert errors[0].source == "SemanticValidator"


def test_classify_context_errors():
    classifier = SQLErrorClassifier()

    errors = classifier.classify_context(
        ["Expected DESC ordering but found ASC."]
    )

    assert len(errors) == 1
    assert errors[0].error_type == SQLErrorType.CONTEXT
    assert errors[0].message == "Expected DESC ordering but found ASC."
    assert errors[0].source == "ContextValidator"


def test_classify_multiple_error_types():
    classifier = SQLErrorClassifier()

    errors = classifier.classify(
        syntax_errors=["Invalid SQL."],
        database_errors=["Unknown column."],
        semantic_errors=["Invalid revenue formula."],
        context_errors=["Expected DESC ordering."],
    )

    assert len(errors) == 4

    assert errors[0].error_type == SQLErrorType.SYNTAX
    assert errors[1].error_type == SQLErrorType.DATABASE
    assert errors[2].error_type == SQLErrorType.SEMANTIC
    assert errors[3].error_type == SQLErrorType.CONTEXT


def test_classify_with_no_errors():
    classifier = SQLErrorClassifier()

    errors = classifier.classify()

    assert errors == []