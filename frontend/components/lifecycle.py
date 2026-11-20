
import requests
import streamlit as st

LIFECYCLE_STATUSES = [
    "New",
    "AI Analysed",
    "Under Review",
    "Qualified",
    "Rejected",
    "Follow-up",
    "Converted",
    "Lost",
]


def render_lifecycle_controls(lead, api_base_url):
    lead_id = lead["id"]

    st.subheader(f"Lead #{lead_id} lifecycle")

    current_status = lead.get(
        "lifecycle_status", "AI Analysed"
    )

    if current_status not in LIFECYCLE_STATUSES:
        current_status = "AI Analysed"

    new_status = st.selectbox(
        "Lifecycle status",
        LIFECYCLE_STATUSES,
        index=LIFECYCLE_STATUSES.index(current_status),
        key=f"lifecycle_{lead_id}",
    )

    if st.button(
        "Update lifecycle",
        key=f"update_lifecycle_{lead_id}",
    ):
        try:
            response = requests.patch(
                f"{api_base_url}/api/leads/{lead_id}/lifecycle",
                json={"status": new_status},
                timeout=15,
            )

            if response.ok:
                st.success("Lifecycle updated.")
                st.rerun()
            else:
                st.error(response.json().get("detail", response.text))

        except requests.RequestException as exc:
            st.error(f"API error: {exc}")

    st.divider()
    st.subheader("Lead assignment")

    current_assignee = lead.get("assigned_to") or ""

    assignee = st.text_input(
        "Assigned to",
        value=current_assignee,
        key=f"assignee_{lead_id}",
    )

    if st.button(
        "Save assignment",
        key=f"assign_{lead_id}",
    ):
        try:
            response = requests.patch(
                f"{api_base_url}/api/leads/{lead_id}/assign",
                json={"assigned_to": assignee or None},
                timeout=15,
            )

            if response.ok:
                st.success("Assignment saved.")
                st.rerun()
            else:
                st.error(response.text)

        except requests.RequestException as exc:
            st.error(f"API error: {exc}")

    st.divider()
    st.subheader("Human review notes")

    notes = st.text_area(
        "Internal notes",
        value=lead.get("review_notes") or "",
        height=120,
        key=f"notes_{lead_id}",
    )

    if st.button(
        "Save notes",
        key=f"notes_save_{lead_id}",
    ):
        try:
            response = requests.patch(
                f"{api_base_url}/api/leads/{lead_id}/notes",
                json={"review_notes": notes or None},
                timeout=15,
            )

            if response.ok:
                st.success("Review notes saved.")
                st.rerun()
            else:
                st.error(response.text)

        except requests.RequestException as exc:
            st.error(f"API error: {exc}")
