
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "tests" / "data" / "lead_evaluation.json"


def load_evaluation_data():
    if not DATA_PATH.exists():
        st.error(f"Evaluation dataset not found: {DATA_PATH}")
        return []

    try:
        with DATA_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            st.error("Evaluation dataset must contain a JSON list.")
            return []

        return data

    except (json.JSONDecodeError, OSError) as exc:
        st.error(f"Could not load evaluation dataset: {exc}")
        return []


def render_evaluation_dashboard():
    st.title("🧪 Lead Intelligence Evaluation")
    st.caption(
        "Evaluate the rule-based lead prioritization system "
        "against manually labelled examples."
    )

    from app.services.lead_service import (
        extract_with_rules,
        calculate_lead_score,
    )

    cases = load_evaluation_data()

    if not cases:
        st.warning("Add valid evaluation records to continue.")
        return

    results = []

    for case in cases:
        profile = extract_with_rules(
            case["enquiry"],
            case.get("name"),
            case.get("email"),
            case.get("company"),
        )

        score, priority, action = calculate_lead_score(profile)

        results.append({
            "Lead ID": case["id"],
            "Expected Priority": case["expected_priority"],
            "Predicted Priority": priority,
            "Score": score,
            "Correct": priority == case["expected_priority"],
            "Recommended Action": action,
            "Expected Service": case["expected_service"],
            "Predicted Service": profile.get(
                "requested_service", "Not specified"
            ),
            "Service Correct": (
                profile.get("requested_service", "Not specified")
                == case["expected_service"]
            ),
            "Expected Intent": case["expected_intent"],
            "Predicted Intent": profile.get("intent", "unknown"),
            "Intent Correct": (
                profile.get("intent", "unknown")
                == case["expected_intent"]
            ),
        })

    df = pd.DataFrame(results)

    accuracy = accuracy_score(
        df["Expected Priority"],
        df["Predicted Priority"],
    )
    service_accuracy = df["Service Correct"].mean()
    intent_accuracy = df["Intent Correct"].mean()
    correct = int(df["Correct"].sum())
    total = len(df)

    st.subheader("Performance Overview")

    col1, col2, col3, col4, col5  = st.columns(5)

    col1.metric("Accuracy", f"{accuracy:.1%}")
    col2.metric("Correct Predictions", f"{correct}/{total}")
    col3.metric("Evaluation Records", total)
    col4.metric("Service Extraction Accuracy", f"{service_accuracy:.1%}",)
    col5.metric("Buying Intent Accuracy", f"{intent_accuracy:.1%}",)

    st.divider()

    st.subheader("Priority Classification Report")

    report = classification_report(
        df["Expected Priority"],
        df["Predicted Priority"],
        labels=["Low", "Medium", "High"],
        output_dict=True,
        zero_division=0,
    )

    report_df = pd.DataFrame(report).transpose()
    st.dataframe(report_df.round(3), use_container_width=True)

    st.divider()

    st.subheader("Confusion Matrix")

    labels = ["Low", "Medium", "High"]

    matrix = confusion_matrix(
        df["Expected Priority"],
        df["Predicted Priority"],
        labels=labels,
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=labels,
        columns=labels,
    )

    fig = px.imshow(
        matrix_df,
        text_auto=True,
        labels={
            "x": "Predicted Priority",
            "y": "Actual Priority",
            "color": "Number of Leads",
        },
        title="Actual vs Predicted Priority",
        aspect="auto",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Extraction Quality")

    extraction_metrics = pd.DataFrame({
        "Metric": [
            "Priority Classification",
            "Service Extraction",
            "Buying Intent Detection",
        ],
        "Accuracy": [
            accuracy,
            service_accuracy,
            intent_accuracy,
        ],
    })

    st.dataframe(
        extraction_metrics.style.format({"Accuracy": "{:.1%}"}),
        use_container_width=True,
        hide_index=True,
    )
    
    st.divider()
    st.subheader("Lead Evaluation Details")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    incorrect = df[~df["Correct"]]

    st.subheader("Misclassified Leads")

    if incorrect.empty:
        st.success("No misclassified leads in this evaluation dataset.")
    else:
        st.warning(
            f"{len(incorrect)} lead(s) require scoring-rule review."
        )
        st.dataframe(
            incorrect,
            use_container_width=True,
            hide_index=True,
        )

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download Evaluation Results",
        data=csv,
        file_name="lead_evaluation_results.csv",
        mime="text/csv",
    )

    st.info(
        "These results reflect a small, manually labelled dataset. "
        "They should not be interpreted as production performance."
    )
