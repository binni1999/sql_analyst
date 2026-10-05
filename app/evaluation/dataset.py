import json
from pathlib import Path

from evaluation.models import EvaluationCase, EvaluationDataset


DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "sql_analyst_cases.json"
)


def load_evaluation_dataset(
    path: str | Path | None = None,
) -> EvaluationDataset:
    """Load and validate an evaluation dataset from JSON."""

    dataset_path = Path(path) if path is not None else DEFAULT_DATASET_PATH

    with dataset_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    dataset = EvaluationDataset.model_validate(payload)

    case_ids = [case.case_id for case in dataset.cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Evaluation dataset contains duplicate case_id values")

    return dataset


def load_evaluation_cases(
    path: str | Path | None = None,
) -> list[EvaluationCase]:
    """Convenience loader returning only the cases."""

    return load_evaluation_dataset(path).cases
