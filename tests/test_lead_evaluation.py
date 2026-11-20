import json
from pathlib import Path

import pytest

from app.services.lead_service import (
    extract_with_rules,
    calculate_lead_score,
)


DATA_PATH = Path(__file__).parent / "data" / "lead_evaluation.json"


@pytest.fixture
def evaluation_cases():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@pytest.mark.parametrize(
    "case_index",
    range(5),
)
def test_evaluation_case_has_required_fields(evaluation_cases, case_index):
    case = evaluation_cases[case_index]

    for field in [
        "id",
        "enquiry",
        "expected_priority",
        "expected_service",
        "expected_intent",
    ]:
        assert case.get(field)


def test_evaluation_dataset_has_unique_ids(evaluation_cases):
    ids = [case["id"] for case in evaluation_cases]
    assert len(ids) == len(set(ids))


def test_evaluation_outputs_are_valid(evaluation_cases):
    for case in evaluation_cases:
        profile = extract_with_rules(
            case["enquiry"],
            case.get("name"),
            case.get("email"),
            case.get("company"),
        )

        score, priority, action = calculate_lead_score(profile)

        assert 0 <= score <= 100
        assert priority in {"High", "Medium", "Low"}
        assert isinstance(action, str)
        assert action.strip()