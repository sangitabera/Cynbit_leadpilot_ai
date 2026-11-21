
import pandas as pd
import streamlit as st

from .lifecycle import (
    render_lifecycle_controls,
)


PIPELINE_STAGES = [
    "New",
    "AI Analysed",
    "Under Review",
    "Qualified",
    "Follow-up",
    "Converted",
    "Rejected",
    "Lost",
]


def render_pipeline(leads, api_base_url):
    st.title("Sales Pipeline")
    st.caption("Manage lead progress and human-reviewed decisions.")

    if not leads:
        st.info("No leads available.")
        return

    df = pd.DataFrame(leads)

    for stage in PIPELINE_STAGES:
        count = sum(
            lead.get("lifecycle_status", "AI Analysed") == stage
            for lead in leads
        )

        st.metric(stage, count)

    st.divider()

    selected_stage = st.selectbox(
        "Filter by lifecycle stage",
        ["All"] + PIPELINE_STAGES,
    )

    search = st.text_input(
        "Search by name, company or email"
    ).strip().lower()

    filtered = [
        lead for lead in leads
        if (
            selected_stage == "All"
            or lead.get("lifecycle_status", "AI Analysed")
            == selected_stage
        )
        and (
            not search
            or search in str(lead.get("name") or "").lower()
            or search in str(lead.get("company") or "").lower()
            or search in str(lead.get("email") or "").lower()
        )
    ]

    if not filtered:
        st.info("No leads match your filters.")
        return

    st.dataframe(
        pd.DataFrame([
            {
                "ID": lead.get("id"),
                "Company": lead.get("company"),
                "Priority": lead.get("priority"),
                "Score": lead.get("priority_score"),
                "Lifecycle": lead.get("lifecycle_status"),
                "Approval": lead.get("approval_status"),
                "Assigned to": lead.get("assigned_to"),
            }
            for lead in filtered
        ]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    selected_id = st.selectbox(
        "Select a lead to manage",
        [lead["id"] for lead in filtered],
        format_func=lambda lead_id: (
            f"#{lead_id} — "
            + str(next(
                lead.get("company") or lead.get("name") or "Unknown"
                for lead in filtered
                if lead["id"] == lead_id
            ))
        ),
    )

    selected_lead = next(
        lead for lead in filtered
        if lead["id"] == selected_id
    )

    with st.expander(
        f"Manage Lead #{selected_id}",
        expanded=True,
    ):
        st.write("**Enquiry:**")
        st.write(selected_lead.get("enquiry", "Unavailable"))

        st.write(
            f"**Approval:** {selected_lead.get('approval_status', 'Pending')}"
        )

        render_lifecycle_controls(
            selected_lead,
            api_base_url,
        )
