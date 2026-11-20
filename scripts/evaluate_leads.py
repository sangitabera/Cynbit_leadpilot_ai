import json
import sys
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.lead_service import (
    extract_with_rules,
    calculate_lead_score,
)

DATA_PATH = ROOT / "tests" / "data" / "lead_evaluation.json"


def evaluate():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    expected = []
    predicted = []

    print("\nCYNBIT LEADPILOT AI — EVALUATION")
    print("=" * 55)

    for case in cases:
        profile = extract_with_rules(
            case["enquiry"],
            case.get("name"),
            case.get("email"),
            case.get("company"),
        )

        score, priority, action = calculate_lead_score(profile)

        expected.append(case["expected_priority"])
        predicted.append(priority)

        print(f"\nLead: {case['id']}")
        print(f"Expected priority: {case['expected_priority']}")
        print(f"Predicted priority: {priority}")
        print(f"Score: {score}/100")
        print(f"Action: {action}")

    labels = ["Low", "Medium", "High"]

    print("\n" + "=" * 55)
    print("PRIORITY CLASSIFICATION METRICS")
    print("=" * 55)

    print(f"Accuracy: {accuracy_score(expected, predicted):.2%}")

    print("\nClassification Report:")
    print(
        classification_report(
            expected,
            predicted,
            labels=labels,
            zero_division=0,
        )
    )

    print("Confusion Matrix:")
    print(confusion_matrix(expected, predicted, labels=labels))

    print("\nNote: Results use a small, manually labelled evaluation dataset.")
    print("They are preliminary and should not be presented as production accuracy.")


if __name__ == "__main__":
    evaluate()